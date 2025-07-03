'use strict';
const { Model } = require('sequelize');
module.exports = (sequelize, DataTypes) => 
  {
  class Vacation extends Model 
  {
    static associate(models) 
    { 
      Vacation.belongsTo(models.Employee, { foreignKey: 'employeeId' });
    }
  }
  Vacation.init({
    startDate: DataTypes.DATE,
    endDate: DataTypes.DATE,
    days: DataTypes.INTEGER,
    status: DataTypes.STRING
  }, {
    sequelize,
    modelName: 'Vacation',
  });
  return Vacation;
};