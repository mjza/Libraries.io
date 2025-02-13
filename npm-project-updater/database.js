require('dotenv').config();
const { Pool } = require('pg');

// PostgreSQL Connection
const pool = new Pool({
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
});

// Create the Projects Table (if not exists)
const createTable = async () => {
  const query = `
    CREATE TABLE IF NOT EXISTS Projects (
      id SERIAL PRIMARY KEY,
      name TEXT NOT NULL UNIQUE,
      platform TEXT NOT NULL DEFAULT 'NPM',
      description TEXT,
      homepage TEXT,
      repository_url TEXT,
      package_manager_url TEXT,
      keywords TEXT[],
      raw JSONB
    );
  `;
  try {
    await pool.query(query);
    console.log("✅ [DATABASE] Projects table is ready.");
  } catch (err) {
    console.error("❌ [DATABASE ERROR]", err);
  }
};

// Insert or Update NPM Packages
const insertPackage = async (name, rawData) => {
  const query = `
    INSERT INTO Projects (name, platform, raw)
    VALUES ($1, 'NPM', $2)
    ON CONFLICT (name, platform) DO NOTHING;
  `;
  try {
    await pool.query(query, [name, rawData]);
  } catch (err) {
    console.error(`❌ [DB ERROR] Failed to insert ${name}:`, err);
  }
};

module.exports = { pool, createTable, insertPackage };
