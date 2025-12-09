// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');
const stylexPlugin = require('@stylexjs/eslint-plugin');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*'],
    plugins: {
      '@stylexjs': stylexPlugin,
    },
    rules: {
      '@stylexjs/sort-keys': 'error',
      '@stylexjs/valid-styles': 'error',
      '@stylexjs/no-unused': 'error',
    },
  },
]);
