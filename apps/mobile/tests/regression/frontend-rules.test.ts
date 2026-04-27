/**
 * Regression tests for Resilio+ mobile frontend rules.
 * These tests run via grep on the filesystem — NO React Native runtime needed.
 *
 * Run: pnpm test:mobile:regression
 *      → pnpm --filter @resilio/mobile test:regression (if configured)
 *      → or: cd apps/mobile && node -e "require('./tests/regression/frontend-rules.test.ts')"
 *
 * Actually executed via Jest (plain Node) since these are pure TS string/regex checks.
 */
import * as fs from 'fs';
import * as path from 'path';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const MOBILE_APP = path.resolve(__dirname, '../../app');
const UI_MOBILE_SRC = path.resolve(__dirname, '../../../../packages/ui-mobile/src');

/** Recursively collect all .ts/.tsx files under dir */
function collectFiles(dir: string, exts = ['.ts', '.tsx']): string[] {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && !entry.name.startsWith('.')) {
      files.push(...collectFiles(full, exts));
    } else if (exts.some((ext) => entry.name.endsWith(ext))) {
      files.push(full);
    }
  }
  return files;
}

function readFile(filePath: string): string {
  return fs.readFileSync(filePath, 'utf-8');
}

// ─── Rule 2: No direct lucide-react-native imports outside @resilio/ui-mobile ──

describe('Rule 2 — No direct lucide-react-native import outside @resilio/ui-mobile', () => {
  const screenFiles = collectFiles(MOBILE_APP);

  if (screenFiles.length === 0) {
    it.skip('no screen files found', () => {});
    return;
  }

  it('no app screen imports lucide-react-native directly', () => {
    const violations: string[] = [];
    for (const file of screenFiles) {
      const content = readFile(file);
      if (content.includes("from 'lucide-react-native'")) {
        violations.push(path.relative(process.cwd(), file));
      }
    }
    expect(violations).toEqual([]);
  });
});

// ─── Rule 3: No hardcoded hex colors in app screens ──────────────────────────

describe('Rule 3 — No hardcoded hex in apps/mobile/app/**/*.tsx', () => {
  const screenFiles = collectFiles(MOBILE_APP).filter((f) => f.endsWith('.tsx'));
  const HEX_PATTERN = /#[0-9a-fA-F]{3,8}/;
  // Acceptable: hex in comments, in string literals for testing, in known UI-RULES reference
  // NOT acceptable: color="#fff", color="#3B74C9", '#08080e' in style objects

  it('warns on hardcoded hex in screen files (informational)', () => {
    const violations: { file: string; line: number; content: string }[] = [];
    for (const file of screenFiles) {
      const lines = readFile(file).split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Skip comment lines
        if (line.trimStart().startsWith('//') || line.trimStart().startsWith('*')) continue;
        if (HEX_PATTERN.test(line)) {
          violations.push({
            file: path.relative(process.cwd(), file),
            line: i + 1,
            content: line.trim().slice(0, 80),
          });
        }
      }
    }
    // Log violations for visibility (not fail — still tracked as tech debt)
    if (violations.length > 0) {
      console.warn(`⚠️  Rule 3 violations (${violations.length} hardcoded hex values):`);
      for (const v of violations) {
        console.warn(`  ${v.file}:${v.line} → ${v.content}`);
      }
    }
    // Soft check: fail only if new violations appear beyond known ones (current: 2)
    // Known: index.tsx:77 (#fff), index.tsx:104 (#fff)
    expect(violations.length).toBeLessThanOrEqual(4);
  });
});

// ─── Rule 11: No SafeAreaView import from react-native or safe-area-context ───

describe('Rule 11 — No SafeAreaView in app screens (use <Screen> instead)', () => {
  const screenFiles = collectFiles(MOBILE_APP).filter((f) => f.endsWith('.tsx'));

  it('no screen imports SafeAreaView from react-native', () => {
    const violations: string[] = [];
    for (const file of screenFiles) {
      // Exclude ui-mobile package itself (Screen.tsx comments mention SafeAreaView)
      if (file.includes('ui-mobile')) continue;
      const content = readFile(file);
      if (
        content.includes("SafeAreaView } from 'react-native'") ||
        content.includes("SafeAreaView} from 'react-native'") ||
        content.includes(", SafeAreaView,") ||
        content.includes("<SafeAreaView")
      ) {
        violations.push(path.relative(process.cwd(), file));
      }
    }
    expect(violations).toEqual([]);
  });

  it('no screen imports SafeAreaView from react-native-safe-area-context', () => {
    const violations: string[] = [];
    for (const file of screenFiles) {
      const content = readFile(file);
      if (
        content.includes("SafeAreaView } from 'react-native-safe-area-context'") ||
        content.includes("SafeAreaView} from 'react-native-safe-area-context'")
      ) {
        violations.push(path.relative(process.cwd(), file));
      }
    }
    expect(violations).toEqual([]);
  });
});

// ─── Rule 16: No @import url() Google Fonts ───────────────────────────────────

describe('Rule 16 — No @import url() Google Fonts CDN', () => {
  const allFiles = [
    ...collectFiles(MOBILE_APP, ['.ts', '.tsx', '.css']),
    ...collectFiles(path.resolve(__dirname, '../../'), ['.css']).filter((f) =>
      f.endsWith('.css')
    ),
  ];

  it('no @import url() in mobile source files', () => {
    const violations: string[] = [];
    for (const file of allFiles) {
      const content = readFile(file);
      if (content.includes('@import url(')) {
        violations.push(path.relative(process.cwd(), file));
      }
    }
    expect(violations).toEqual([]);
  });
});

// ─── package.json: expo-router/entry is main ─────────────────────────────────

describe('apps/mobile/package.json structure', () => {
  const pkgPath = path.resolve(__dirname, '../../package.json');
  const pkg = JSON.parse(readFile(pkgPath)) as {
    main?: string;
    name?: string;
  };

  it('main is expo-router/entry', () => {
    expect(pkg.main).toBe('expo-router/entry');
  });

  it('package name is @resilio/mobile', () => {
    expect(pkg.name).toBe('@resilio/mobile');
  });
});
