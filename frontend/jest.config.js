/**
 * Jest configuration for AutoAdmin frontend testing
 * Comprehensive setup for React Native, component, and integration testing
 */

const {defaults} = require('jest-config');

module.exports = {
  // Test environment - use jsdom for React Native testing
  testEnvironment: 'jsdom',

  // Automatically clear mock calls, instances, contexts and results before every test
  clearMocks: true,
  restoreMocks: true,
  resetMocks: true,

  // Indicates whether the coverage information should be collected while executing the test
  collectCoverage: true,

  // An array of glob patterns indicating a set of files for which coverage information should be collected
  collectCoverageFrom: [
    'app/**/*.{js,jsx,ts,tsx}',
    'components/**/*.{js,jsx,ts,tsx}',
    'services/**/*.{js,jsx,ts,tsx}',
    'utils/**/*.{js,jsx,ts,tsx}',
    'hooks/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.expo/**',
    '!**/coverage/**',
    '!**/e2e/**',
    '!**/android/**',
    '!**/ios/**',
    '!**/*.config.{js,ts}',
    '!**/babel.config.{js}',
    '!**/jest.config.{js}'
  ],

  // The directory where Jest should output its coverage files
  coverageDirectory: 'coverage',

  // Coverage report formats
  coverageReporters: ['text', 'lcov', 'html', 'json-summary'],

  // Thresholds for code coverage
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70
    },
    // Higher threshold for critical components and services
    'app/api/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    },
    'services/agents/': {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },

  // The root directory that Jest should scan for tests and modules within
  rootDir: '.',

  // A list of paths to directories that Jest should use to search for files in
  roots: ['<rootDir>'],

  // The glob patterns Jest uses to detect test files
  testMatch: [
    '**/__tests__/**/*.{js,jsx,ts,tsx}',
    '**/*.{test,spec}.{js,jsx,ts,tsx}',
    'tests/**/*.{test,spec}.{js,jsx,ts,tsx}'
  ],

  // An array of regexp pattern strings that are matched against all test paths, matching paths are ignored
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.expo/',
    '/coverage/',
    '/e2e/',
    '/android/',
    '/ios/',
    '/dist/'
  ],

  // A map from regular expressions to module names or to arrays of module names that allow to stub out resources with a single module
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '^@components/(.*)$': '<rootDir>/components/$1',
    '^@services/(.*)$': '<rootDir>/services/$1',
    '^@hooks/(.*)$': '<rootDir>/hooks/$1',
    '^@utils/(.*)$': '<rootDir>/utils/$1',
    '^@app/(.*)$': '<rootDir>/app/$1',
    '^@tests/(.*)$': '<rootDir>/tests/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|webp|avif|svg)$': '<rootDir>/__mocks__/fileMock.js'
  },

  // An array of file extensions your modules use
  moduleFileExtensions: [
    ...defaults.moduleFileExtensions,
    'ts',
    'tsx',
    'js',
    'jsx',
    'json',
    'node'
  ],

  // Setup files
  setupFiles: ['<rootDir>/tests/setup/jest.setup.js'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup/jest.setupAfterEnv.js'],

  // Disable projects for now to avoid missing setup files
  // projects: [

  // Transform files with TypeScript and React Native
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', {
      presets: [
        ['@babel/preset-env', { targets: { node: 'current' } }],
        '@babel/preset-react',
        '@babel/preset-typescript'
      ]
    }],
    '^.+\\.(json|png|jpg|jpeg|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': '<rootDir>/tests/setup/fileTransform.js'
  },

  // Transform ignore patterns for React Native modules
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|expo|@expo|@react-navigation|react-native-svg|react-native-reanimated|@react-native-async-storage|@react-native-community|react-native-vector-icons)/)'
  ],

  // Module path mappings
  moduleDirectories: ['node_modules', '<rootDir>'],

  // Global variables
  globals: {
    __DEV__: true,
    __TEST__: true,
    'ts-jest': {
      isolatedModules: true
    }
  },

  // Test timeout
  testTimeout: 10000,

  // Verbose output
  verbose: true,

  // Worker threads for parallel test execution
  maxWorkers: '50%',

  // Cache directory
  cacheDirectory: '<rootDir>/.jest-cache',

  // Custom reporters
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: 'coverage',
        outputName: 'junit.xml',
        classNameTemplate: '{classname}',
        titleTemplate: '{title}',
        ancestorSeparator: ' › ',
        usePathForSuiteName: true
      }
    ]
  ],

  // Projects for different test types - commented out to avoid missing setup files
  // projects: [

  // Snapshot configuration - commented out
  // snapshotSerializers: ['<rootDir>/tests/setup/snapshotSerializers.js'],

  // Error handling
  errorOnDeprecated: true,

  // Performance optimizations
  // haste configuration removed due to Jest warnings

  // Mock patterns
  modulePathIgnorePatterns: ['<rootDir>/dist/']
};