const express = require('express');
const router = express.Router();

const feriasAppController = require('../controllers/feriasAppController');

router.get('/', feriasAppController.showDashboard);

module.exports = router;