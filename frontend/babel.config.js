module.exports = function(api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      [
        '@stylexjs/babel-plugin',
        {
          dev: process.env.NODE_ENV === 'development',
          test: process.env.NODE_ENV === 'test',
          runtimeInjection: false,
          treeshakeCompensation: true,
          unstable_moduleResolution: {
            type: 'commonJS',
          },
        },
      ],
    ],
  };
};