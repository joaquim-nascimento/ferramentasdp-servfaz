module.exports = (req, res, next) => 
{
  return next();
  
  if (req.session.user) { return next(); }

  res.redirect('/auth/login');
};