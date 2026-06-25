const express = require('express');
const { v4: uuidv4 } = require('uuid');
const { getDb } = require('../db');

const router = express.Router();

function getStripe() {
  const Stripe = require('stripe');
  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey || stripeKey.startsWith('sk_test_...') || stripeKey === 'change-me') return null;
  return new Stripe(stripeKey);
}

router.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  const stripe = getStripe();
  if (!stripe) {
    console.error('Stripe not configured, webhook ignored');
    return res.status(200).json({ received: true, warning: 'Stripe not configured' });
  }

  const sig = req.headers['stripe-signature'];
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
  } catch (err) {
    return res.status(400).json({ error: 'Invalid signature' });
  }

  const db = getDb();
  const existingEvent = db.prepare('SELECT id FROM stripe_events WHERE stripe_event_id = ?').get(event.id);
  if (existingEvent) return res.status(200).json({ received: true, duplicate: true });

  db.prepare('INSERT INTO stripe_events (id, stripe_event_id, type, data, processed_at) VALUES (?, ?, ?, ?, datetime(\'now\'))').run(uuidv4(), event.id, event.type, JSON.stringify(event.data));

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object;
        const { customer, subscription, metadata } = session;
        if (!metadata?.userId || !metadata?.tier) break;
        const sub = await stripe.subscriptions.retrieve(subscription);
        db.prepare("UPDATE subscriptions SET stripe_subscription_id = ?, status = 'active', current_period_start = ?, current_period_end = ?, updated_at = datetime('now') WHERE user_id = ? AND tier = ? AND status = 'incomplete'").run(subscription, new Date(sub.current_period_start * 1000).toISOString(), new Date(sub.current_period_end * 1000).toISOString(), metadata.userId, metadata.tier);
        break;
      }
      case 'invoice.paid': {
        const invoice = event.data.object;
        if (!invoice.subscription) break;
        db.prepare("UPDATE subscriptions SET status = 'active', current_period_start = ?, current_period_end = ?, updated_at = datetime('now') WHERE stripe_subscription_id = ?").run(new Date(invoice.period_start * 1000).toISOString(), new Date(invoice.period_end * 1000).toISOString(), invoice.subscription);
        break;
      }
      case 'invoice.payment_failed': {
        const failed = event.data.object;
        if (failed.subscription) db.prepare("UPDATE subscriptions SET status = 'past_due', updated_at = datetime('now') WHERE stripe_subscription_id = ?").run(failed.subscription);
        break;
      }
      case 'customer.subscription.updated': {
        const subUpdate = event.data.object;
        const s = subUpdate.current_period_start ? new Date(subUpdate.current_period_start * 1000).toISOString() : null;
        const e = subUpdate.current_period_end ? new Date(subUpdate.current_period_end * 1000).toISOString() : null;
        const dbStatus = subUpdate.status === 'active' ? 'active' : subUpdate.status === 'past_due' ? 'past_due' : subUpdate.status === 'canceled' ? 'canceled' : subUpdate.status;
        db.prepare("UPDATE subscriptions SET status = ?, current_period_start = ?, current_period_end = ?, updated_at = datetime('now') WHERE stripe_subscription_id = ?").run(dbStatus, s, e, subUpdate.id);
        break;
      }
      case 'customer.subscription.deleted': {
        db.prepare("UPDATE subscriptions SET status = 'canceled', updated_at = datetime('now') WHERE stripe_subscription_id = ?").run(event.data.object.id);
        break;
      }
    }
    res.status(200).json({ received: true });
  } catch (err) {
    console.error('Webhook handler error:', err);
    res.status(500).json({ error: 'Webhook handler error' });
  }
});

module.exports = router;