// Temporary script to process frontend-metadata.json for verification report
const fs = require('fs');
const path = require('path');

const data = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'frontend-metadata.json'), 'utf8'
));

// === 1. Group by directory ===
const dirGroups = {};
data.files.forEach(f => {
  const rel = f.path.replace('frontend/', '');
  const parts = rel.split('/');
  parts.pop();
  const dir = parts.join('/') || '(root)';
  if (!dirGroups[dir]) dirGroups[dir] = [];
  dirGroups[dir].push(f);
});

// === 2. All components ===
const allComponents = [];
data.files.forEach(f => {
  (f.components || []).forEach(c => {
    allComponents.push({ name: c, file: f.path, loc: f.loc });
  });
});

// === 3. All interfaces ===
const allInterfaces = [];
data.files.forEach(f => {
  (f.interfaces || []).forEach(i => {
    allInterfaces.push({ name: i, file: f.path });
  });
});

// === 4. All types ===
const allTypes = [];
data.files.forEach(f => {
  (f.types || []).forEach(t => {
    allTypes.push({ name: t, file: f.path });
  });
});

// === 5. Hooks usage ===
const hooksUsage = {};
data.files.forEach(f => {
  (f.hooks_used || []).forEach(h => {
    if (!hooksUsage[h]) hooksUsage[h] = { count: 0, files: [] };
    hooksUsage[h].count++;
    hooksUsage[h].files.push(f.path);
  });
});
const hooksSorted = Object.entries(hooksUsage)
  .sort((a, b) => b[1].count - a[1].count);

// === 6. Top 20 largest files ===
const top20 = [...data.files].sort((a, b) => b.loc - a.loc).slice(0, 20);

// === 7. Test files ===
const testFiles = data.files.filter(f => f.is_test);

// === 8. Dir stats ===
const dirStats = {};
Object.entries(dirGroups).sort((a, b) => a[0].localeCompare(b[0])).forEach(([dir, files]) => {
  dirStats[dir] = {
    fileCount: files.length,
    totalLoc: files.reduce((s, f) => s + f.loc, 0),
    components: files.reduce((s, f) => s + (f.components ? f.components.length : 0), 0),
    exports: files.reduce((s, f) => s + (f.exports ? f.exports.length : 0), 0),
    interfaces: files.reduce((s, f) => s + (f.interfaces ? f.interfaces.length : 0), 0),
    testFiles: files.filter(f => f.is_test).length,
    files: files.map(f => ({
      name: f.path.split('/').pop(),
      path: f.path,
      loc: f.loc,
      components: f.components || [],
      exports: (f.exports || []).length,
      hooks_used: f.hooks_used || [],
      is_test: f.is_test || false,
      interfaces: (f.interfaces || []).length,
      types: (f.types || []).length
    }))
  };
});

// === Output compact JSON ===
const output = {
  summary: data.summary,
  dirStats,
  allComponents,
  allInterfaces,
  allTypes,
  hooksSorted: hooksSorted.map(([name, data]) => ({ name, count: data.count, files: data.files })),
  top20: top20.map(f => ({ path: f.path, loc: f.loc, components: f.components, exports: (f.exports||[]).length })),
  testFiles: testFiles.map(f => ({ path: f.path, loc: f.loc }))
};

fs.writeFileSync(
  path.join(__dirname, '_frontend-analysis-result.json'),
  JSON.stringify(output, null, 2)
);

// Print compact summary
console.log('=== FRONTEND METADATA ANALYSIS ===');
console.log('Total files:', data.files.length);
console.log('Total LOC:', data.summary.total_loc);
console.log('Total components:', allComponents.length);
console.log('Total interfaces:', allInterfaces.length);
console.log('Total types:', allTypes.length);
console.log('Total exports:', data.summary.total_exports);
console.log('Unique hooks used:', hooksSorted.length);
console.log('Test files:', testFiles.length);
console.log('Directories:', Object.keys(dirStats).length);
console.log('');
console.log('=== TOP 20 FILES ===');
top20.forEach((f, i) => console.log(`${i+1}. ${f.path} (${f.loc} LOC)`));
console.log('');
console.log('=== TOP 30 HOOKS BY USAGE ===');
hooksSorted.slice(0, 30).forEach(([name, d]) => console.log(`  ${name}: ${d.count} files`));
console.log('');
console.log('=== DIR SUMMARY ===');
Object.entries(dirStats).forEach(([dir, s]) => {
  console.log(`  ${dir}: ${s.fileCount} files, ${s.totalLoc} LOC, ${s.components} components, ${s.interfaces} interfaces`);
});
console.log('');
console.log('Result written to _frontend-analysis-result.json');
