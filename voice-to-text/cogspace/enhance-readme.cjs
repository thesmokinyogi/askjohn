#!/usr/bin/env node
// COGSPACE - see cogspace-version.json for version
/**
 * COGSPACE README Enhancement v2.0
 * Intelligently updates README.md based on session work
 * Now with AI-powered Short Description generation!
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// Parse command line arguments
const args = process.argv.slice(2);
const filesChanged = args.find(a => a.startsWith('--files='))?.split('=')[1]?.split(',').filter(f => f) || [];
const features = args.find(a => a.startsWith('--features='))?.split('=')[1]?.split('|').filter(f => f) || [];
const interactive = args.find(a => a.startsWith('--interactive='))?.split('=')[1] === 'true';
const addShortDescription = args.includes('--add-short-description');
const forceShortDescription = args.includes('--force-short-description');

// Main execution
main();

async function main() {
  // Load current README or create template
  let readme = '';
  if (fs.existsSync('README.md')) {
    readme = fs.readFileSync('README.md', 'utf8');
  } else {
    readme = generateDefaultReadme();
  }

  // Handle Short Description generation
  if (addShortDescription || forceShortDescription) {
    const hasShortDesc = readme.includes('## Short Description');

    if (!hasShortDesc || forceShortDescription) {
      console.log('🤖 Generating AI Short Description...');
      try {
        const shortDesc = await generateShortDescription(readme);
        if (shortDesc) {
          readme = insertShortDescription(readme, shortDesc);
          fs.writeFileSync('README.md', readme);
          console.log(`✅ Short Description added: "${shortDesc}"`);
        }
      } catch (err) {
        console.error('⚠️  AI generation failed, using fallback:', err.message);
        const fallbackDesc = extractFallbackDescription(readme);
        if (fallbackDesc) {
          readme = insertShortDescription(readme, fallbackDesc);
          fs.writeFileSync('README.md', readme);
          console.log(`✅ Short Description added (fallback): "${fallbackDesc}"`);
        }
      }
    } else {
      console.log('ℹ️  Short Description already exists');
    }

    if (addShortDescription && !filesChanged.length && !features.length) {
      process.exit(0);
    }
  }

  // Analyze session context
  const sessionContext = analyzeSessionContext(filesChanged, features);

  // Check if there are any meaningful changes to apply
  if (sessionContext.newFeatures.length === 0 &&
      sessionContext.technologies.length === 0 &&
      readme.includes('Last Updated')) {
    // Only timestamp update - auto-apply without prompting
    const enhanced = enhanceReadme(readme, sessionContext);
    fs.writeFileSync('README.md', enhanced);
    console.log('✅ README.md timestamp updated');
    process.exit(0);
  }

  // Enhance README sections
  const enhanced = enhanceReadme(readme, sessionContext);

  // Check if there are actual changes
  if (enhanced === readme) {
    console.log('ℹ️  No README changes needed');
    process.exit(0);
  }

  // Interactive mode - show diff
  if (interactive) {
    console.log('\n📝 README Enhancement Preview:\n');
    showDiff(readme, enhanced);

    const readline = require('readline').createInterface({
      input: process.stdin,
      output: process.stdout
    });

    readline.question('\nApply enhancements? [y/N]: ', (answer) => {
      if (answer.toLowerCase() === 'y') {
        fs.writeFileSync('README.md', enhanced);
        console.log('✅ README.md updated');
        process.exit(0);
      } else {
        console.log('⏭️  Skipped');
        process.exit(1);
      }
      readline.close();
    });
  } else {
    // Auto-apply
    fs.writeFileSync('README.md', enhanced);
    console.log('✅ README.md updated automatically');
    process.exit(0);
  }
}

// ============================================================================
// AI SHORT DESCRIPTION GENERATION
// ============================================================================

async function generateShortDescription(readmeContent) {
  const apiKey = process.env.ANTHROPIC_API_KEY;

  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY not set');
  }

  // Extract first ~2000 chars of README for context
  const context = readmeContent.substring(0, 2000);

  const requestBody = JSON.stringify({
    model: 'claude-3-haiku-20240307',
    max_tokens: 150,
    messages: [{
      role: 'user',
      content: `Summarize this project README in exactly 1-2 sentences (under 150 characters total). Be concise and descriptive. Focus on what the project DOES, not how it works. Output ONLY the summary, no quotes or explanation.

README:
${context}`
    }]
  });

  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.anthropic.com',
      port: 443,
      path: '/v1/messages',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'Content-Length': Buffer.byteLength(requestBody)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const response = JSON.parse(data);
          if (response.content && response.content[0] && response.content[0].text) {
            resolve(response.content[0].text.trim());
          } else if (response.error) {
            reject(new Error(response.error.message));
          } else {
            reject(new Error('Invalid response format'));
          }
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.setTimeout(10000, () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });

    req.write(requestBody);
    req.end();
  });
}

function extractFallbackDescription(readme) {
  // Try to extract from Overview or Description section
  const overviewMatch = readme.match(/## (?:Overview|Description|About)\s*\n+([^\n#]+)/i);
  if (overviewMatch && overviewMatch[1]) {
    const text = overviewMatch[1].trim();
    if (text.length > 10 && !text.startsWith('[')) {
      return text.substring(0, 150);
    }
  }

  // Fallback: first non-empty, non-header line after title
  const lines = readme.split('\n');
  for (let i = 1; i < lines.length && i < 20; i++) {
    const line = lines[i].trim();
    if (line && !line.startsWith('#') && !line.startsWith('*') &&
        !line.startsWith('-') && !line.startsWith('`') && line.length > 20) {
      return line.substring(0, 150);
    }
  }

  return null;
}

function insertShortDescription(readme, description) {
  // Find the first ## header and insert before it
  const lines = readme.split('\n');
  const titleLine = lines.findIndex(l => l.startsWith('# '));
  const firstSectionLine = lines.findIndex((l, i) => i > titleLine && l.startsWith('## '));

  if (firstSectionLine === -1) {
    // No sections, add after title
    lines.splice(titleLine + 1, 0, '', '## Short Description', '', description, '');
  } else {
    // Insert before first section
    lines.splice(firstSectionLine, 0, '## Short Description', '', description, '');
  }

  return lines.join('\n');
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function analyzeSessionContext(files, features) {
  const context = {
    newFiles: files.filter(f => !f.includes('node_modules') && !f.includes('.git')),
    newFeatures: features.filter(f => f && f.length > 0),
    technologies: extractTechnologies(files),
    timestamp: new Date().toISOString().split('T')[0],
  };

  return context;
}

function extractTechnologies(files) {
  const techMap = {
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript React',
    '.jsx': 'React',
    '.py': 'Python',
    '.sh': 'Bash',
    '.json': 'JSON',
    '.md': 'Markdown',
    '.html': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.go': 'Go',
    '.rs': 'Rust',
    '.java': 'Java',
    '.cpp': 'C++',
    '.c': 'C',
  };

  const techs = new Set();
  files.forEach(file => {
    const ext = path.extname(file);
    if (techMap[ext]) techs.add(techMap[ext]);
  });

  return Array.from(techs);
}

function enhanceReadme(current, context) {
  let enhanced = current;

  // Update "Last Updated" if present
  if (enhanced.includes('Last Updated:')) {
    enhanced = enhanced.replace(
      /Last Updated:.*/,
      `Last Updated: ${context.timestamp}`
    );
  }

  // Add new features to Features section
  if (context.newFeatures.length > 0 && enhanced.includes('## Features')) {
    const featuresSection = enhanced.split('## Features')[1]?.split('\n##')[0] || '';
    const existingFeatures = featuresSection.match(/- .*/g) || [];

    context.newFeatures.forEach(feature => {
      const featureLine = `- ${feature}`;
      const featureExists = existingFeatures.some(ef => {
        // Normalize for comparison
        const normalized = ef.replace(/\s*\(New:.*\)/, '').trim();
        return normalized.includes(feature.substring(0, 30)); // Match first 30 chars
      });

      if (!featureExists) {
        // Add new feature after the ## Features header
        enhanced = enhanced.replace(
          /## Features\n/,
          `## Features\n\n${featureLine} *(New: ${context.timestamp})*`
        );
      }
    });
  }

  // Update Technologies section
  if (context.technologies.length > 0) {
    if (enhanced.includes('## Technologies')) {
      const techSection = enhanced.split('## Technologies')[1]?.split('\n##')[0] || '';

      context.technologies.forEach(tech => {
        if (!techSection.includes(tech)) {
          // Add new technology
          enhanced = enhanced.replace(
            /## Technologies\n/,
            `## Technologies\n\n- ${tech}`
          );
        }
      });
    } else {
      // Add Technologies section if it doesn't exist
      const techList = context.technologies.map(t => `- ${t}`).join('\n');
      const techSection = `\n## Technologies\n\n${techList}\n`;

      // Insert before Recent Changes or at the end
      if (enhanced.includes('## Recent Changes')) {
        enhanced = enhanced.replace('## Recent Changes', `${techSection}\n## Recent Changes`);
      } else if (enhanced.includes('## License')) {
        enhanced = enhanced.replace('## License', `${techSection}\n## License`);
      } else {
        enhanced += techSection;
      }
    }
  }

  // Add or update Recent Changes section
  if (context.newFeatures.length > 0 || context.newFiles.length > 0) {
    if (enhanced.includes('## Recent Changes')) {
      // Check if today's date already exists
      if (!enhanced.includes(`### ${context.timestamp}`)) {
        // Add new entry
        const changeEntry = `\n### ${context.timestamp}\n${context.newFeatures.map(f => `- ${f}`).join('\n')}\n`;
        enhanced = enhanced.replace(
          /## Recent Changes\n/,
          `## Recent Changes\n${changeEntry}`
        );
      }
    } else {
      // Add Recent Changes section
      const recentChanges = `\n## Recent Changes\n\n### ${context.timestamp}\n${context.newFeatures.map(f => `- ${f}`).join('\n')}\n`;

      // Insert before License or Contributing
      if (enhanced.includes('## License')) {
        enhanced = enhanced.replace('## License', `${recentChanges}\n## License`);
      } else if (enhanced.includes('## Contributing')) {
        enhanced = enhanced.replace('## Contributing', `${recentChanges}\n## Contributing`);
      } else {
        enhanced += recentChanges;
      }
    }
  }

  return enhanced;
}

function generateDefaultReadme() {
  const projectName = path.basename(process.cwd());
  const timestamp = new Date().toISOString().split('T')[0];

  return `# ${projectName}

## Short Description

[AI will generate a summary on first wake - or add your own 1-2 sentence description here]

## Overview

[Project description will be added]

## Features

- COGSPACE-enabled cognitive workspace
- Session-based development with 90%+ continuity
- Automatic documentation and context preservation

## Technologies

- COGSPACE v35.0 (Portable GitHub DNA)
- Node.js
- Bash scripting

## Getting Started

\`\`\`bash
# Wake up project
./wake.sh

# Save progress
./save.sh "Progress checkpoint"

# End session
./sleep.sh "Session complete"
\`\`\`

## Recent Changes

### ${timestamp}
- Project initialized with COGSPACE DNA

## License

[License information]

---

*Built with COGSPACE - Cognitive workspace serialization*
*Last Updated: ${timestamp}*
`;
}

function showDiff(old, new_) {
  const oldLines = old.split('\n');
  const newLines = new_.split('\n');

  const maxLen = Math.max(oldLines.length, newLines.length);

  for (let i = 0; i < maxLen; i++) {
    const oldLine = oldLines[i];
    const newLine = newLines[i];

    if (oldLine !== newLine) {
      if (!oldLine && newLine) {
        console.log(`\x1b[32m+ ${newLine}\x1b[0m`);
      } else if (oldLine && !newLine) {
        console.log(`\x1b[31m- ${oldLine}\x1b[0m`);
      } else if (oldLine !== newLine) {
        console.log(`\x1b[31m- ${oldLine}\x1b[0m`);
        console.log(`\x1b[32m+ ${newLine}\x1b[0m`);
      }
    }
  }
}


