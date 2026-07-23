import type { Config } from 'jest';
import { createCjsPreset } from 'jest-preset-angular/presets/index.js';

export default {
  ...createCjsPreset(),
  setupFilesAfterEnv: ['<rootDir>/setup-jest.ts'],
  // exceljs importa el build ESM de uuid; Jest necesita el CJS.
  moduleNameMapper: {
    '^uuid$': '<rootDir>/node_modules/.pnpm/uuid@8.3.2/node_modules/uuid/dist/index.js',
  },
  // Conservar el patrón del preset (.mjs / locales) y permitir transformar exceljs.
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@angular/common/locales/.*\\.js$|.*(exceljs|uuid|fast-csv|saxes)/))',
  ],
  coverageThreshold: {
    global: { lines: 60 },
  },
} satisfies Config;
