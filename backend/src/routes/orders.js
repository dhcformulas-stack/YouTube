const express = require('express');
const { v4: uuidv4 } = require('uuid');
const { getDb } = require('../db');
const { authenticateToken } = require('../auth');
const { TIERS } = require('./subscriptions');

const router = express.Router();

// POST /api/orders — Submit a video brief
router.post('/', authenticateToken, (req, res) => {
  try {
    const { title, topic, angle, details, references } = req.body;
    if (!title || !topic) return res.status(400).json({ error: 'Title and topic are required' });

    const db = getDb();

    // Admin users bypass subscription checks
    const user = db.prepare('SELECT role FROM users WHERE id = ?').get(req.user.userId);
    const isAdmin = user && user.role === 'admin';

    let subscription = null;
    if (!isAdmin) {
      subscription = db.prepare("SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active' LIMIT 1").get(req.user.userId);
      if (!subscription) return res.status(403).json({ error: 'Active subscription required to submit video briefs' });

      const tier = TIERS[subscription.tier];
      if (!tier) return res.status(400).json({ error: 'Invalid subscription tier' });

      const periodStart = subscription.current_period_start || new Date().toISOString();
      const videosThisPeriod = db.prepare("SELECT COUNT(*) as count FROM video_briefs WHERE user_id = ? AND created_at >= ? AND status != 'received'").get(req.user.userId, periodStart);
      if (videosThisPeriod.count >= tier.videosPerMonth) {
        return res.status(429).json({ error: `Monthly video limit reached (${tier.videosPerMonth} per month).` });
      }
    }

    const id = uuidv4();
    const refs = Array.isArray(references) ? JSON.stringify(references) : (references || null);

    // For admin without subscription, create or reuse a virtual one
    let subscriptionId;
    if (isAdmin) {
      const adminSub = db.prepare('SELECT id FROM subscriptions WHERE user_id = ? LIMIT 1').get(req.user.userId);
      if (adminSub) {
        subscriptionId = adminSub.id;
      } else {
        subscriptionId = uuidv4();
        db.prepare("INSERT INTO subscriptions (id, user_id, stripe_customer_id, tier, status, created_at, updated_at) VALUES (?, ?, 'admin', 'gold', 'active', datetime('now'), datetime('now'))").run(subscriptionId, req.user.userId);
      }
    } else {
      subscriptionId = subscription.id;
    }

    db.prepare("INSERT INTO video_briefs (id, user_id, subscription_id, title, topic, angle, details, refs, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'received', datetime('now'), datetime('now'))").run(id, req.user.userId, subscriptionId, title.trim(), topic.trim(), angle?.trim() || null, details?.trim() || null, refs);

    const order = db.prepare('SELECT * FROM video_briefs WHERE id = ?').get(id);
    if (order.refs) { try { order.refs = JSON.parse(order.refs); } catch (e) { /* ok */ } }

    res.status(201).json({ message: 'Video brief submitted successfully', order });
  } catch (err) {
    console.error('Create order error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/orders — List user's orders
router.get('/', authenticateToken, (req, res) => {
  try {
    const db = getDb();
    const orders = db.prepare('SELECT * FROM video_briefs WHERE user_id = ? ORDER BY created_at DESC').all(req.user.userId);
    const parsed = orders.map(o => { if (o.refs) { try { o.refs = JSON.parse(o.refs); } catch (e) { /* ok */ } } return o; });
    res.json({ orders: parsed });
  } catch (err) {
    console.error('List orders error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/orders/:id
router.get('/:id', authenticateToken, (req, res) => {
  try {
    const db = getDb();
    const order = db.prepare('SELECT * FROM video_briefs WHERE id = ? AND user_id = ?').get(req.params.id, req.user.userId);
    if (!order) return res.status(404).json({ error: 'Order not found' });
    if (order.refs) { try { order.refs = JSON.parse(order.refs); } catch (e) { /* ok */ } }
    res.json({ order });
  } catch (err) {
    console.error('Get order error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/orders/:id — Cancel if still in 'received' status
router.delete('/:id', authenticateToken, (req, res) => {
  try {
    const db = getDb();
    const order = db.prepare('SELECT * FROM video_briefs WHERE id = ? AND user_id = ?').get(req.params.id, req.user.userId);
    if (!order) return res.status(404).json({ error: 'Order not found' });
    if (order.status !== 'received') return res.status(400).json({ error: 'Cannot cancel an order already in progress. Current status: ' + order.status });
    db.prepare('DELETE FROM video_briefs WHERE id = ?').run(order.id);
    res.json({ message: 'Order canceled successfully' });
  } catch (err) {
    console.error('Delete order error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/orders/:id/status — Update order status
router.put('/:id/status', authenticateToken, (req, res) => {
  try {
    const { status, videoUrl } = req.body;
    const validStatuses = ['received', 'researching', 'scripting', 'production', 'rendering', 'delivered'];
    if (!status || !validStatuses.includes(status)) return res.status(400).json({ error: 'Invalid status' });

    const db = getDb();
    const order = db.prepare('SELECT * FROM video_briefs WHERE id = ?').get(req.params.id);
    if (!order) return res.status(404).json({ error: 'Order not found' });
    if (order.user_id !== req.user.userId) return res.status(403).json({ error: 'Unauthorized' });

    const now = new Date().toISOString();
    if (videoUrl && status === 'delivered') {
      db.prepare('UPDATE video_briefs SET status = ?, video_url = ?, updated_at = ? WHERE id = ?').run(status, videoUrl, now, order.id);
    } else {
      db.prepare('UPDATE video_briefs SET status = ?, updated_at = ? WHERE id = ?').run(status, now, order.id);
    }
    const updated = db.prepare('SELECT * FROM video_briefs WHERE id = ?').get(order.id);
    res.json({ message: 'Order status updated', order: updated });
  } catch (err) {
    console.error('Update order status error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;