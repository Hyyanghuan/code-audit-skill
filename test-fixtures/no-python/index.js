/**
 * 无 Python 项目 - 仅 JavaScript
 */
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.json({ status: 'ok' });
});

module.exports = app;
