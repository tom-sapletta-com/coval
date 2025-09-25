// Complete working code here
const express = require('express');
const app = express();
app.use(express.json());

app.get('/', (req, res) => {
  res.send({ status: 'ok' });
});

app.listen(3000, () => {
  console.log('Frontend server is running on port 3000');
});