'use strict';
const { Model } = require('sequelize');
module.exports = (sequelize, DataTypes) => 
  {
  class Employee extends Model 
  {
    static associate(models) 
    { 
      Employee.hasMany(models.Vacation, { foreignKey: 'employeeId' });
    }
  }
  Employee.init({
    name: DataTypes.STRING,
    admissionDate: DataTypes.DATE,
    registration: DataTypes.STRING,
    contractNumber: DataTypes.STRING,
    lastVacationDate: DataTypes.DATE,
    vacationDays: DataTypes.INTEGER,
    absenceDays: DataTypes.INTEGER,
    absence: DataTypes.STRING,
    isEligible: DataTypes.BOOLEAN
  }, {
    sequelize,
    modelName: 'Employee',
  });
  return Employee;
};