const nextJest = require('next/jest');
module.exports = nextJest({ dir: './' })({
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/src/$1' },
  testMatch: ['<rootDir>/tests/unit/**/*.test.ts', '<rootDir>/tests/components/**/*.test.tsx'],
});
