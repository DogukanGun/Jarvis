#!/usr/bin/env node

/**
 * Simple build script for packages
 * Runs TypeScript compiler (tsc) in the current directory
 */

import { execSync } from 'child_process';
import { existsSync, rmSync } from 'fs';
import { resolve } from 'path';

const cwd = process.cwd();
const distDir = resolve(cwd, 'dist');

console.log(`Building package in ${cwd}...`);

// Clean dist directory
if (existsSync(distDir)) {
  console.log('Cleaning dist directory...');
  rmSync(distDir, { recursive: true, force: true });
}

// Run TypeScript compiler
try {
  console.log('Running tsc...');
  execSync('npx tsc', { cwd, stdio: 'inherit' });
  console.log('Build complete!');
} catch (error) {
  console.error('Build failed!');
  process.exit(1);
}
