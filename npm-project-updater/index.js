require('dotenv').config();
const allPackages = require('all-the-package-names');
const { createTable, insertPackage } = require('./database');

// Fetch and Store NPM Package Names
const updateNpmPackages = async () => {
  console.log("🔍 Fetching NPM package names...");
  
  const packageNames = allPackages;  // Fetches all package names
  
  console.log(`📦 Found ${packageNames.length} packages. Inserting into database...`);
  
  for (let i = 0; i < packageNames.length; i++) {
    const packageName = packageNames[i];
    
    // Insert package into database
    await insertPackage(packageName, JSON.stringify({ name: packageName }));
    
    if ((i + 1) % 1000 === 0) {
      console.log(`✅ Inserted ${i + 1} packages...`);
    }
  }

  console.log("🎉 All NPM packages have been updated.");
};

// Main Execution
(async () => {
  await createTable();
  await updateNpmPackages();
})();
