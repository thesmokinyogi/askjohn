#!/usr/bin/env node
// COGSPACE Version Helper - Single source of truth
// All scripts should use this module to get version information

const fs = require('fs');
const path = require('path');

/**
 * Get COGSPACE version information from cogspace-version.json
 * @returns {Object} Version information object
 */
function getVersion() {
    const versionFile = path.join(__dirname, '..', 'cogspace-version.json');
    try {
        const data = JSON.parse(fs.readFileSync(versionFile, 'utf8'));
        return {
            version: data.version,
            versionName: data.versionName,
            full: `COGSPACE v${data.version}`,
            display: `v${data.version} "${data.versionName}"`,
            buildDate: data.buildDate,
            previousVersion: data.previousVersion
        };
    } catch (err) {
        console.error('Warning: Could not read cogspace-version.json:', err.message);
        return {
            version: 'unknown',
            versionName: 'unknown',
            full: 'COGSPACE',
            display: 'unknown',
            buildDate: null,
            previousVersion: null
        };
    }
}

/**
 * Get version string for script headers
 * @returns {string} Header comment string
 */
function getHeaderComment() {
    const v = getVersion();
    return `// COGSPACE ${v.display} - see cogspace-version.json for details`;
}

module.exports = { getVersion, getHeaderComment };

// CLI support: run directly to print version
if (require.main === module) {
    const v = getVersion();
    console.log(v.full);
}
