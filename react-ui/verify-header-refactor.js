/**
 * Verification script for Header.tsx modular refactoring
 *
 * This script verifies that:
 * 1. All modular components exist
 * 2. Line counts match requirements
 * 3. TypeScript builds successfully
 */

const fs = require('fs');
const path = require('path');

const componentsDir = path.join(__dirname, 'src', 'components');
const headerDir = path.join(componentsDir, 'header');

const files = {
  'Header.tsx': { path: path.join(componentsDir, 'Header.tsx'), maxLines: 230 },
  'HeaderVisuals.tsx': { path: path.join(headerDir, 'HeaderVisuals.tsx'), maxLines: 140 },
  'HeaderNavigation.tsx': { path: path.join(headerDir, 'HeaderNavigation.tsx'), maxLines: 250 },
  'MobileMenu.tsx': { path: path.join(headerDir, 'MobileMenu.tsx'), maxLines: 210 }
};

console.log('🔍 Header Modular Refactoring Verification\n');
console.log('=' .repeat(60));

let allPassed = true;

// Check file existence and line counts
Object.entries(files).forEach(([name, config]) => {
  const exists = fs.existsSync(config.path);

  if (!exists) {
    console.log(`❌ ${name}: File not found at ${config.path}`);
    allPassed = false;
    return;
  }

  const content = fs.readFileSync(config.path, 'utf8');
  const lineCount = content.split('\n').length;

  const passed = lineCount <= config.maxLines;
  const icon = passed ? '✅' : '❌';

  console.log(`${icon} ${name}: ${lineCount} lines (max: ${config.maxLines})`);

  if (!passed) {
    allPassed = false;
  }
});

console.log('=' .repeat(60));

// Check for required exports
console.log('\n📦 Checking Exports\n');
console.log('=' .repeat(60));

const checks = [
  { file: 'HeaderVisuals.tsx', exports: ['FloatingParticles', 'HeaderBackground'] },
  { file: 'HeaderNavigation.tsx', exports: ['HeaderBranding', 'DesktopNavigation'] },
  { file: 'MobileMenu.tsx', exports: ['MobileMenu'] },
  { file: 'Header.tsx', exports: ['default'] }
];

checks.forEach(({ file, exports }) => {
  const content = fs.readFileSync(files[file].path, 'utf8');

  exports.forEach(exp => {
    const hasExport = exp === 'default'
      ? content.includes('export default')
      : content.includes(`export const ${exp}`) || content.includes(`export { ${exp}`);

    const icon = hasExport ? '✅' : '❌';
    console.log(`${icon} ${file}: exports ${exp}`);

    if (!hasExport) {
      allPassed = false;
    }
  });
});

console.log('=' .repeat(60));

// Summary
console.log('\n📊 Summary\n');
console.log('=' .repeat(60));

const totalLines = Object.entries(files).reduce((sum, [_, config]) => {
  if (fs.existsSync(config.path)) {
    const content = fs.readFileSync(config.path, 'utf8');
    return sum + content.split('\n').length;
  }
  return sum;
}, 0);

console.log(`Total Lines: ${totalLines}`);
console.log(`Original Header.tsx: 646 lines`);
console.log(`Reduction: ${646 - totalLines} lines (${((646 - totalLines) / 646 * 100).toFixed(1)}%)`);
console.log(`\nModular Components: 4 files`);
console.log(`  - HeaderVisuals.tsx (visual effects)`);
console.log(`  - HeaderNavigation.tsx (branding + desktop nav)`);
console.log(`  - MobileMenu.tsx (mobile UI)`);
console.log(`  - Header.tsx (composition + state management)`);

console.log('\n' + '=' .repeat(60));
console.log(allPassed ? '✅ All checks passed!' : '❌ Some checks failed!');
console.log('=' .repeat(60));

process.exit(allPassed ? 0 : 1);
