const express = require('express');
const { v4: uuidv4 } = require('uuid');
const { getDb } = require('../db');
const { authenticateToken } = require('../auth');

const router = express.Router();

function getStripe() {
  const Stripe = require('stripe');
  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey || stripeKey.startsWith('sk_test_...') || stripeKey === 'change-me') {
    return null;
  }
  return new Stripe(stripeKey);
}

const TIERS = {
  starter: { name: 'Starter', amount: 9900, currency: 'usd', videosPerMonth: 1, description: '1 video per month, standard production quality' },
  intermediate: { name: 'Intermediate', amount: 24999, currency: 'usd', videosPerMonth: 2, description: '2 videos per month, priority research & production' },
  gold: { name: 'Gold', amount: 49999, currency: 'usd', videosPerMonth: 4, description: '4 videos per month, dedicated researcher, expedited delivery, premium production' }
};

// GET /api/subscriptions/tiers
router.get('/tiers', (req, res) => {
  const tiers = Object.entries(TIERS).map(([key, value]) => ({
    id: key, name: value.name, amount: value.amount, currency: value.currency,
    videosPerMonth: value.videosPerMonth, description: value.description,
    formattedPrice: `$${(value.amount / 100).toFixed(2)}/mo`
  }));
  res.json({ tiers });
});

// POST /api/subscriptions/create-checkout
router.post('/create-checkout', authenticateToken, async (req, res) => {
  try {
    const { tier, successUrl, cancelUrl } = req.body;
    if (!tier || !TIERS[tier]) {
      return res.status(400).json({ error: 'Invalid tier. Must be: starter, intermediate, or gold' });
    }

    const stripe = getStripe();
    if (!stripe) {
      return res.status(503).json({ error: 'Payment service not configured. Set STRIPE_SECRET_KEY.' });
    }

    const db = getDb();
    const user = db.prepare('SELECT id, email, name FROM users WHERE id = ?').get(req.user.userId);
    if (!user) return res.status(404).json({ error: 'User not found' });

    const existingSub = db.prepare("SELECT id, stripe_customer_id FROM subscriptions WHERE user_id = ? AND status = 'active' LIMIT 1").get(req.user.userId);
    if (existingSub) return res.status(409).json({ error: 'You already have an active subscription' });

    const tierConfig = TIERS[tier];

    let customerId;
    const existingCustomer = db.prepare('SELECT stripe_customer_id FROM subscriptions WHERE user_id = ? AND stripe_customer_id IS NOT NULL LIMIT 1').get(req.user.userId);
    if (existingCustomer) {
      customerId = existingCustomer.stripe_customer_id;
    } else {
      const customer = await stripe.customers.create({ email: user.email, name: user.name, metadata: { userId: user.id } });
      customerId = customer.id;
    }

    let priceId = process.env[`STRIPE_PRICE_${tier.toUpperCase()}`];
    if (!priceId || priceId.startsWith('price_')) {
      const product = await stripe.products.create({ name: `Chronicle Forge - ${tierConfig.name}`, description: tierConfig.description, metadata: { tier } });
      const price = await stripe.prices.create({ product: product.id, unit_amount: tierConfig.amount, currency: tierConfig.currency, recurring: { interval: 'month' }, metadata: { tier } });
      priceId = price.id;
    }

    const session = await stripe.checkout.sessions.create({
      customer: customerId, mode: 'subscription',
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: successUrl || `${process.env.FRONTEND_URL || 'http://localhost:3000'}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl || `${process.env.FRONTEND_URL || 'http://localhost:3000'}/pricing`,
      metadata: { userId: user.id, tier }
    });

    const subId = uuidv4();
    db.prepare('INSERT INTO subscriptions (id, user_id, stripe_customer_id, tier, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?,\'incomplete\', datetime(\'now\'), datetime(\'now\'))').run(subId, user.id, customerId, tier);

    res.json({ sessionId: session.id, sessionUrl: session.url, subscriptionId: subId });
  } catch (err) {
    console.error('Checkout session error:', err);
    res.status(500).json({ error: 'Failed to create checkout session' });
  }
});

// GET /api/subscriptions/my
router.get('/my', authenticateToken, (req, res) => {
  try {
    const db = getDb();
    const subscription = db.prepare('SELECT id, tier, status, current_period_start, current_period_end, created_at FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1').get(req.user.userId);
    if (!subscription) return res.json({ subscription: null });

    const videoCount = db.prepare("SELECT COUNT(*) as count FROM video_briefs WHERE user_id = ? AND status = 'delivered'").get(req.user.userId);
    const tier = TIERS[subscription.tier];

    res.json({ subscription: { ...subscription, videosUsedThisMonth: videoCount.count, videosAllowed: tier ? tier.videosPerMonth : 0 } });
  } catch (err) {
    console.error('Get subscription error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/subscriptions/cancel
router.post('/cancel', authenticateToken, async (req, res) => {
  try {
    const stripe = getStripe();
    if (!stripe) return res.status(503).json({ error: 'Payment service not configured.' });

    const db = getDb();
    const subscription = db.prepare("SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active' LIMIT 1").get(req.user.userId);
    if (!subscription) return res.status(404).json({ error: 'No active subscription found' });

    if (subscription.stripe_subscription_id) {
      await stripe.subscriptions.update(subscription.stripe_subscription_id, { cancel_at_period_end: true });
    }

    db.prepare("UPDATE subscriptions SET status = 'canceled', updated_at = datetime('now') WHERE id = ?").run(subscription.id);
    res.json({ message: 'Subscription canceled' });
  } catch (err) {
    console.error('Cancel subscription error:', err);
    res.status(500).json({ error: 'Failed to cancel subscription' });
  }
});

module.exports = router;
module.exports.TIERS = TIERS;