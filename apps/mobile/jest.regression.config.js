/** @type {import('jest').Config} */
module.exports = {
  // Pure Node environment — no React Native needed (filesystem + regex only)
  testEnvironment: 'node',
  transform: {
    '^.+\\.tsx?$': ['babel-jest', { presets: ['babel-preset-expo'] }],
  },
  testMatch: ['**/tests/regression/**/*.test.ts'],
  // Transpile all node_modules that might have ESM syntax
  transformIgnorePatterns: [],
};
