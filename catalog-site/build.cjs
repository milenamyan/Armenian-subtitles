/* Run for every Render deployment; no dependencies required. */
const fs=require('node:fs'),path=require('node:path');
const metadata={updated_at:new Date().toISOString()};
fs.writeFileSync(path.join(__dirname,'deployment.json'),JSON.stringify(metadata)+'\n');
console.log('Updated deployment date.');
