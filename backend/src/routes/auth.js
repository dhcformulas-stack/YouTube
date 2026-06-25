const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');
const { getDb } = require('../db');
const { authenticateToken } = require('../auth');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-in-production';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';

// POST /api/auth/signup
router.post('/signup', async (req, res) => {
  try {
    const { email, password, name } = req.body;

    if (!email || !password || !name) {
      return res.status(400).json({ error: 'Email, password, and name are required' });
    }

    if (password.length < 8) {
      return res.status(400).json({ error: 'Password must be at least 8 characters' });
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({ error: 'Invalid email format' });
    }

    const db = getDb();

    const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(email.toLowerCase());
    if (existing) {
      return res.status(409).json({ error: 'Email already registered' });
    }

    const saltRounds = 10;
    const passwordHash = await bcrypt.hash(password, saltRounds);

    const id = uuidv4();
    const now = new Date().toISOString();

    db.prepare(`
      INSERT INTO users (id, email, password_hash, name, role, created_at, updated_at)
      VALUES (?, ?, ?, ?, 'user', ?, ?)
    `).run(id, email.toLowerCase(), passwordHash, name.trim(), now, now);

    const token = jwt.sign(
      { userId: id, email: email.toLowerCase(), name: name.trim(), role: 'user' },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    res.status(201).json({
      message: 'Account created successfully',
      token,
      user: { id, email: email.toLowerCase(), name: name.trim(), role: 'user' }
    });
  } catch (err) {
    console.error('Signup error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/auth/login
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' });
    }

    const db = getDb();
    const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email.toLowerCase());

    if (!user) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    const passwordMatch = await bcrypt.compare(password, user.password_hash);
    if (!passwordMatch) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    const token = jwt.sign(
      { userId: user.id, email: user.email, name: user.name, role: user.role },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    res.json({
      message: 'Login successful',
      token,
      user: { id: user.id, email: user.email, name: user.name, role: user.role }
    });
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/auth/me
router.get('/me', authenticateToken, (req, res) => {
  try {
    const db = getDb();
    const user = db.prepare('SELECT id, email, name, role, created_at FROM users WHERE id = ?').get(req.user.userId);

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    const subscription = db.prepare(`
      SELECT id, tier, status, current_period_start, current_period_end
      FROM subscriptions WHERE user_id = ? AND status = 'active'
      ORDER BY created_at DESC LIMIT 1
    `).get(req.user.userId);

    res.json({ user, subscription: subscription || null });
  } catch (err) {
    console.error('Profile error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/auth/profile
router.put('/profile', authenticateToken, (req, res) => {
  try {
    const { name } = req.body;
    const db = getDb();

    if (!name || !name.trim()) {
      return res.status(400).json({ error: 'Name is required' });
    }

    const now = new Date().toISOString();
    db.prepare('UPDATE users SET name = ?, updated_at = ? WHERE id = ?')
      .run(name.trim(), now, req.user.userId);

    res.json({ message: 'Profile updated', name: name.trim() });
  } catch (err) {
    console.error('Profile update error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;