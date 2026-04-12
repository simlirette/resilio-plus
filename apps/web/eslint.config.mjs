import tseslint from 'typescript-eslint'

/** @type {import('eslint').Linter.Config[]} */
export default [
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      parser: tseslint.parser,
    },
    rules: {
      // A — No direct lucide-react imports outside @resilio/ui-web
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['lucide-react'],
              message: 'Use Icon from @resilio/ui-web',
            },
            {
              group: ['lucide-react-native'],
              message: 'Use Icon from @resilio/ui-mobile',
            },
          ],
        },
      ],
      // C — warn globally (incremental migration in progress)
      'no-restricted-syntax': [
        'warn',
        {
          selector:
            "JSXAttribute[name.name='style'] Literal[value=/#[0-9a-fA-F]{3,8}/]",
          message: 'Use CSS variables from design-tokens',
        },
      ],
    },
  },
  // C at error level for already-migrated files
  {
    files: [
      'src/app/check-in/page.tsx',
      'src/app/energy/page.tsx',
    ],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector:
            "JSXAttribute[name.name='style'] Literal[value=/#[0-9a-fA-F]{3,8}/]",
          message: 'Use CSS variables from design-tokens',
        },
      ],
    },
  },
]
