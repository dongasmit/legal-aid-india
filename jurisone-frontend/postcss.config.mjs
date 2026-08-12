const config = {
  plugins: {
    "@tailwindcss/postcss": {
      base: import.meta.dirname || process.cwd(),
    },
  },
};

export default config;
