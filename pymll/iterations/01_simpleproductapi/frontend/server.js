// Complete working code here
const express = require('express');
const app = express();
app.get('/', (req, res) => {
    res.send({ status: 'ok' });
});
const PORT = process.env.PORT || 3003;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});