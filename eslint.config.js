import js from '@eslint/js';
import prettier from 'eslint-config-prettier';

export default [
  // Base configuration for all JavaScript files
  {
    files: ['frontend/src/js/**/*.js', 'static/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'script', // Legacy script architecture, not ES modules
      globals: {
        // Browser globals
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        alert: 'readonly',
        confirm: 'readonly',
        prompt: 'readonly',
        requestAnimationFrame: 'readonly',

        // Modern browser APIs
        FormData: 'readonly',
        Headers: 'readonly',
        Request: 'readonly',
        Response: 'readonly',
        AbortController: 'readonly',
        AbortSignal: 'readonly',

        // Application globals (legacy architecture - available globally)
        CONFIG: 'readonly',
        apiService: 'readonly',
        authService: 'readonly',
        themeService: 'readonly',
        app: 'writable',
        MarktplaatsSearchApp: 'writable'
      }
    },
    rules: {
      // Extend recommended rules
      ...js.configs.recommended.rules,

      // Relax rules for legacy architecture
      'no-unused-vars': ['warn', {
        vars: 'all',
        args: 'after-used',
        varsIgnorePattern: '^(SearchForm|SearchManager|ResultsViewer|formatInterval|switchView|\\$|\\$\\$|escapeHtml|cleanText|truncateText|formatDate|formatDateTime|formatTimeAgo|debounce|setLoading|showAlert)$'
      }],

      // Code quality rules
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-alert': 'off', // Legacy code uses alert/confirm
      'no-undef': 'error',
      'no-redeclare': 'error',
      'no-shadow': 'error',

      // Best practices
      'eqeqeq': ['error', 'always'],
      'curly': ['error', 'all'],
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-script-url': 'error',
      'no-sequences': 'error',
      'no-throw-literal': 'error',
      'no-unmodified-loop-condition': 'error',
      'no-unused-expressions': ['error', { allowShortCircuit: true, allowTernary: true }],
      'no-useless-call': 'error',
      'no-useless-concat': 'error',
      'no-useless-return': 'error',
      'prefer-promise-reject-errors': 'error',
      'radix': 'error',
      'yoda': 'error',

      // Modern JavaScript features (where possible)
      'prefer-const': 'error',
      'no-var': 'error',
      'prefer-template': 'error',
      'template-curly-spacing': ['error', 'never'],

      // Style rules (basic - prettier will handle most formatting)
      'indent': ['error', 2, { SwitchCase: 1 }],
      'quotes': ['error', 'single', { avoidEscape: true }],
      'semi': ['error', 'always'],
      'comma-dangle': ['error', 'never'],
      'object-curly-spacing': ['error', 'always'],
      'array-bracket-spacing': ['error', 'never'],
      'space-before-blocks': 'error',
      'keyword-spacing': 'error',
      'space-infix-ops': 'error',
      'no-trailing-spaces': 'error',
      'eol-last': 'error',

      // Function rules
      'function-paren-newline': ['error', 'consistent'],
      'space-before-function-paren': ['error', {
        anonymous: 'always',
        named: 'never',
        asyncArrow: 'always'
      }],

      // Error prevention
      'no-unreachable': 'error',
      'no-constant-condition': 'error',
      'no-dupe-args': 'error',
      'no-dupe-keys': 'error',
      'no-duplicate-case': 'error',
      'no-empty': 'error',
      'no-ex-assign': 'error',
      'no-extra-boolean-cast': 'error',
      'no-func-assign': 'error',
      'no-invalid-regexp': 'error',
      'no-irregular-whitespace': 'error',
      'no-obj-calls': 'error',
      'no-sparse-arrays': 'error',
      'use-isnan': 'error',
      'valid-typeof': 'error'
    }
  },

  // Special configuration for constants.js (uses export)
  {
    files: ['frontend/src/js/config/constants.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module' // This file uses ES modules
    }
  },

  // Ignore patterns
  {
    ignores: [
      'frontend/dist/**/*',
      'node_modules/**/*',
      '**/*.min.js',
      '**/build/**/*',
      '**/coverage/**/*',
      '**/.git/**/*'
    ]
  },

  // Prettier integration (must be last)
  prettier
];
