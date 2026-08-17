const { PrismaClient } = require('./node_modules/@prisma/client');
const prisma = new PrismaClient();

async function main() {
  try {
    await prisma.$connect();
    console.log('Database connection successful');
    
    // Try a simple query
    const userCount = await prisma.user.count();
    console.log(`User count: ${userCount}`);
    
    await prisma.$disconnect();
  } catch (error) {
    console.error('Database connection failed:', error);
    process.exit(1);
  }
}

main();
