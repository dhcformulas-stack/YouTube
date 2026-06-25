const express = require('express');
const { getDb } = require('../db');
const { authenticateToken } = require('../auth');
const { requireAdmin } = require('../middleware/adminAuth');

const router = express.Router();

// GET /api/admin/stats
router.get('/stats', authenticateToken, requireAdmin, (req, res) => {
  try {
    const db = getDb();
    const totalUsers = db.prepare('SELECT COUNT(*) as count FROM users').get();
    const totalOrders = db.prepare('SELECT COUNT(*) as count FROM video_briefs').get();
    const activeSubscriptions = db.prepare("SELECT COUNT(*) as count FROM subscriptions WHERE status = 'active'").get();
    const deliveredVideos = db.prepare("SELECT COUNT(*) as count FROM video_briefs WHERE status = 'delivered'").get();
    const ordersByStatus = db.prepare('SELECT status, COUNT(*) as count FROM video_briefs GROUP BY status').all();
    const subscriptionsByTier = db.prepare("SELECT tier, COUNT(*) as count FROM subscriptions WHERE status = 'active' GROUP BY tier").all();

    res.json({ stats: { totalUsers: totalUsers.count, totalOrders: totalOrders.count, activeSubscriptions: activeSubscriptions.count, deliveredVideos: deliveredVideos.count, ordersByStatus, subscriptionsByTier } });
  } catch (err) {
    console.error('Admin stats error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/admin/users
router.get('/users', authenticateToken, requireAdmin, (req, res) => {
  try {
    const db = getDb();
    const users = db.prepare(`
      SELECT u.id, u.email, u.name, u.role, u.created_at,
        (SELECT COUNT(*) FROM video_briefs WHERE user_id = u.id) as total_orders,
        (SELECT COUNT(*) FROM video_briefs WHERE user_id = u.id AND status = 'delivered') as delivered_orders,
        (SELECT tier FROM subscriptions WHERE user_id = u.id AND status = 'active' LIMIT 1) as current_tier
      FROM users u ORDER BY u.created_at DESC
    `).all();
    res.json({ users });
  } catch (err) {
    console.error('Admin list users error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/admin/users/:id
router.get('/users/:id', authenticateToken, requireAdmin, (req, res) => {
  try {
    const db = getDb();
    const user = db.prepare('SELECT id, email, name, role, created_at, updated_at FROM users WHERE id = ?').get(req.params.id);
    if (!user) return res.status(404).json({ error: 'User not found' });

    const subscription = db.prepare('SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1').get(req.params.id);
    const orders = db.prepare('SELECT * FROM video_briefs WHERE user_id = ? ORDER BY created_at DESC').all(req.params.id);
    res.json({ user, subscription: subscription || null, orders });
  } catch (err) {
    console.error('Admin get user error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/admin/orders
router.get('/orders', authenticateToken, requireAdmin, (req, res) => {
  try {
    const db = getDb();
    const status = req.query.status;
    const limit = Math.min(parseInt(req.query.limit) || 50, 200);
    const offset = parseInt(req.query.offset) || 0;

    let sql = 'SELECT v.*, u.email as user_email, u.name as user_name FROM video_briefs v JOIN users u ON v.user_id = u.id';
    const params = [];
    if (status) { sql += ' WHERE v.status = ?'; params.push(status); }
    sql += ' ORDER BY v.created_at DESC LIMIT ? OFFSET ?';
    params.push(limit, offset);

    const orders = db.prepare(sql).all(...params);
    const parsed = orders.map(o => { if (o.refs) { try { o.refs = JSON.parse(o.refs); } catch (e) { /* ok */ } } return o; });
    res.json({ orders: parsed, limit, offset });
  } catch (err) {
    console.error('Admin list orders error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/admin/orders/:id
router.get('/orders/:id', authenticateToken, requireAdmin, (req, res) => {
  try {
    const db = getDb();
    const order = db.prepare('SELECT v.*, u.email as user_email, u.name as user_name FROM video_briefs v JOIN users u ON v.user_id = u.id WHERE v.id = ?').get(req.params.id);
    if (!order) return res.status(404).json({ error: 'Order not found' });
    if (order.refs) { try { order.refs = JSON.parse(order.refs); } catch (e) { /* ok */ } }
    res.json({ order });
  } catch (err) {
    console.error('Admin get order error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/admin/orders/:id/status
router.put('/orders/:id/status', authenticateToken, requireAdmin, (req, res) => {
  try {
    const { status, videoUrl } = req.body;
    const validStatuses = ['received', 'researching', 'scripting', 'production', 'rendering', 'delivered'];
    if (!status || !validStatuses.includes(status)) return res.status(400).json({ error: 'Invalid status' });

    const db = getDb();
    const order = db.prepare('SELECT * FROM video_briefs WHERE id = ?').get(req.params.id);
    if (!order) return res.status(404).json({ error: 'Order not found' });

    const now = new Date().toISOString();
    if (videoUrl && status === 'delivered') {
      db.prepare('UPDATE video_briefs SET status = ?, video_url = ?, updated_at = ? WHERE id = ?').run(status, videoUrl, now, order.id);
    } else {
      db.prepare('UPDATE video_briefs SET status = ?, updated_at = ? WHERE id = ?').run(status, now, order.id);
    }
    const updated = db.prepare('SELECT * FROM video_briefs WHERE id = ?').get(order.id);
    res.json({ message: 'Order status updated', order: updated });
  } catch (err) {
    console.error('Admin update order error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;