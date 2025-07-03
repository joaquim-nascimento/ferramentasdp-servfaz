const { Employee, Vacation } = require('../models');

exports.showDashboard = async (req, res) => 
{
  try 
  {
    const employees = await Employee.findAll();
    const vacations = await Vacation.findAll();

    const employeeCount = employees.length;
    const vacationCount = vacations.length;

    res.render('ferias-app/dashboard', { employeeCount, vacationCount });
  } 
  catch (error) 
  {
    console.error(error);
    res.status(500).send('Erro ao mostrar dashboard');
  }
};