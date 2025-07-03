const express = require('express');
const router = express.Router();

router.get('/login', (req, res) => { res.render('login', { error: null } ); });

router.get('/logout', (req, res) => { req.session.destroy(() => { res.redirect('/login'); }); });

const USER = { name: 'admin', password: 'servfaz.app' }

router.post('/login', (req, res) => 
{
    const { name, password } = req.body;
    
    if (name === USER.name && password === USER.password) 
    {
        req.session.user = name;
        return res.redirect('/');
    }

    res.render('login', { error: 'Credenciais inválidas' });
});

module.exports = router;