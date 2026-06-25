require('dotenv').config();

const express = require('express');
const cors = require('cors');
const path = require('path');

const { getDb, closeDb, seedAdminUser } = require('./db');

const authRoutes = require('./routes/auth');
const subscriptionRoutes = require('./routes/subscriptions');
const orderRoutes = require('./routes/orders');
const adminRoutes = require('./routes/admin');
const webhookRoutes = require('./stripe/webhooks');

const app = express();
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';

app.use(cors({ origin: FRONTEND_URL, credentials: true, methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], allowedHeaders: ['Content-Type', 'Authorization'] }));
app.use(express.json());

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'Chronicle Forge API', version: '1.0.0', timestamp: new Date().toISOString() });
});

app.use('/api/auth', authRoutes);
app.use('/api/subscriptions', subscriptionRoutes);
app.use('/api/orders', orderRoutes);
app.use('/api/admin', adminRoutes);
app.use('/api/stripe', webhookRoutes);

const frontendBuildPath = path.join(__dirname, '..', '..', 'frontend', 'dist');
app.use(express.static(frontendBuildPath));

app.use((req, res) => {
  if (req.path.startsWith('/api')) return res.status(404).json({ error: 'API endpoint not found' });
  res.sendFile(path.join(frontendBuildPath, 'index.html'), (err) => {
    if (err) res.status(200).json({ message: 'Chronicle Forge API is running. Frontend not built yet.' });
  });
});

try {
  const db = getDb();
  console.log('Database initialized successfully');
  seedAdminUser().catch(err => console.error('Admin seeding error:', err));
} catch (err) {
  console.error('Failed to initialize database:', err);
  process.exit(1);
}

const server = app.listen(PORT, HOST, () => {
  console.log(`Chronicle Forge API running on http://${HOST}:${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
});

process.on('SIGTERM', () => { closeDb(); server.close(() => process.exit(0)); });
process.on('SIGINT', () => { closeDb(); server.close(() => process.exit(0)); });

module.exports = app;