const express   = require('express');
const flash     = require('express-flash');
const session   = require('express-session');
const path      = require('path');
const sequelize = require('./config/database');

const authRoutes     = require('./routes/authRoutes');
const employeeRoutes = require('./routes/employeeRoutes');
const vacationRoutes = require('./routes/vacationRoutes');

const appRoutes       = require('./routes/appRoutes');
const feriasAppRoutes = require('./routes/feriasAppRoutes');
const pontoAppRoutes  = require('./routes/pontoAppRoutes');
const fgtsAppRoutes   = require('./routes/fgtsAppRoutes');

const app = express();

// Configurações
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Middlewares
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(session({ secret: 's3rV-S3crET-F4Z-k3y-4pp', resave: false, saveUninitialized: false }));
app.use(flash());

const auth = require('./middlewares/auth');

// Rotas
app.use('/auth', authRoutes);
app.use('/employees', auth, employeeRoutes);
app.use('/vacations', auth, vacationRoutes);

app.use('/', auth, appRoutes)
app.use('/ferias', auth, feriasAppRoutes);
app.use('/ponto', auth, pontoAppRoutes);
app.use('/fgts', auth, fgtsAppRoutes);

// Sincronizar banco de dados e iniciar servidor
sequelize.sync().then(() => { app.listen(3000, () => { console.log('Servidor rodando na porta 3000'); }); });