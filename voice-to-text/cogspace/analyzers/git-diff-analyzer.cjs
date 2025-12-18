// COGSPACE v40.0.0
/**
 * COGSPACE v32.0.0 Git Diff Analyzer
 * Tracks code changes through git diff analysis
 *
 * @module git-diff-analyzer
 * @version 32.0.0
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * Analyze git changes since last session
 * @param {string} projectPath - Path to project directory
 * @param {string} sinceCommit - Commit hash or ref to compare from (optional)
 * @returns {Object} Git diff analysis with file categorization
 */
function analyzeGitChanges(projectPath, sinceCommit = null) {
  try {
    // Change to project directory
    process.chdir(projectPath);

    // Check if git repo
    if (!isGitRepository()) {
      return createEmptyAnalysis('Not a git repository');
    }

    // Get diff data
    const diffStat = getDiffStat(sinceCommit);
    const changedFiles = getChangedFiles(sinceCommit);
    const fileDetails = analyzeFileChanges(changedFiles);

    // Categorize changes
    const categories = categorizeChanges(fileDetails);

    // Generate summary
    const summary = generateSummary(fileDetails, categories);

    return {
      timestamp: new Date().toISOString(),
      projectPath,
      sinceCommit: sinceCommit || 'working-directory',
      summary,
      categories,
      fileDetails: fileDetails.slice(0, 100), // Limit to 100 files
      diffStat,
      metadata: {
        totalFiles: fileDetails.length,
        totalAdditions: diffStat.additions,
        totalDeletions: diffStat.deletions,
        netChange: diffStat.additions - diffStat.deletions
      }
    };
  } catch (error) {
    return createEmptyAnalysis(`Error: ${error.message}`);
  }
}

/**
 * Check if current directory is a git repository
 */
function isGitRepository() {
  try {
    execSync('git rev-parse --git-dir', { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

/**
 * Get diff statistics
 */
function getDiffStat(sinceCommit) {
  try {
    const cmd = sinceCommit
      ? `git diff --shortstat ${sinceCommit}`
      : 'git diff --shortstat HEAD';

    const output = execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });

    // Parse output: "X files changed, Y insertions(+), Z deletions(-)"
    const match = output.match(/(\d+)\s+file.*?(\d+)\s+insertion.*?(\d+)\s+deletion/);

    if (match) {
      return {
        filesChanged: parseInt(match[1]),
        additions: parseInt(match[2]),
        deletions: parseInt(match[3])
      };
    }

    // Try alternate format for additions only
    const addMatch = output.match(/(\d+)\s+file.*?(\d+)\s+insertion/);
    if (addMatch) {
      return {
        filesChanged: parseInt(addMatch[1]),
        additions: parseInt(addMatch[2]),
        deletions: 0
      };
    }

    return { filesChanged: 0, additions: 0, deletions: 0 };
  } catch {
    return { filesChanged: 0, additions: 0, deletions: 0 };
  }
}

/**
 * Get list of changed files
 */
function getChangedFiles(sinceCommit) {
  try {
    const cmd = sinceCommit
      ? `git diff --name-status ${sinceCommit}`
      : 'git diff --name-status HEAD';

    const output = execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });

    if (!output.trim()) {
      // Check for untracked files
      const untrackedCmd = 'git ls-files --others --exclude-standard';
      const untracked = execSync(untrackedCmd, { encoding: 'utf8', stdio: 'pipe' });

      if (untracked.trim()) {
        return untracked.trim().split('\n').map(file => ({
          status: 'A',
          file: file.trim()
        }));
      }

      return [];
    }

    return output.trim().split('\n').map(line => {
      const parts = line.split('\t');
      return {
        status: parts[0].trim(),
        file: parts[1]?.trim() || ''
      };
    }).filter(item => item.file);
  } catch {
    return [];
  }
}

/**
 * Analyze individual file changes
 */
function analyzeFileChanges(changedFiles) {
  return changedFiles.map(({ status, file }) => {
    const fileType = categorizeFileType(file);
    const changeType = mapStatusToChangeType(status);

    return {
      file,
      status,
      changeType,
      fileType,
      extension: path.extname(file).substring(1) || 'none',
      directory: path.dirname(file),
      stats: getFileStats(file, status)
    };
  });
}

/**
 * Categorize file by type
 */
function categorizeFileType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const basename = path.basename(filePath).toLowerCase();

  // Code files
  const codeExts = ['.js', '.cjs', '.mjs', '.ts', '.tsx', '.jsx', '.py', '.java', '.go', '.rs', '.cpp', '.c', '.h'];
  if (codeExts.includes(ext)) return 'code';

  // Documentation
  const docExts = ['.md', '.txt', '.rst', '.adoc'];
  if (docExts.includes(ext) || basename.startsWith('readme')) return 'documentation';

  // Configuration
  const configExts = ['.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.config'];
  const configFiles = ['package.json', '.gitignore', '.env', 'dockerfile', 'makefile'];
  if (configExts.includes(ext) || configFiles.includes(basename)) return 'configuration';

  // Test files
  if (filePath.includes('test') || filePath.includes('spec') || basename.includes('.test.') || basename.includes('.spec.')) {
    return 'test';
  }

  // Styles
  const styleExts = ['.css', '.scss', '.sass', '.less'];
  if (styleExts.includes(ext)) return 'style';

  // Markup
  const markupExts = ['.html', '.xml', '.svg'];
  if (markupExts.includes(ext)) return 'markup';

  // Data
  const dataExts = ['.csv', '.tsv', '.sql', '.db'];
  if (dataExts.includes(ext)) return 'data';

  // Scripts
  const scriptExts = ['.sh', '.bash', '.zsh', '.fish', '.ps1'];
  if (scriptExts.includes(ext)) return 'script';

  return 'other';
}

/**
 * Map git status to change type
 */
function mapStatusToChangeType(status) {
  const statusMap = {
    'A': 'added',
    'M': 'modified',
    'D': 'deleted',
    'R': 'renamed',
    'C': 'copied',
    'U': 'unmerged',
    'T': 'type-changed'
  };
  return statusMap[status] || 'unknown';
}

/**
 * Get file-specific stats
 */
function getFileStats(file, status) {
  if (status === 'D') {
    return { additions: 0, deletions: 0, net: 0 };
  }

  try {
    const output = execSync(`git diff --numstat HEAD -- "${file}"`, {
      encoding: 'utf8',
      stdio: 'pipe'
    });

    if (output.trim()) {
      const parts = output.trim().split('\t');
      const additions = parseInt(parts[0]) || 0;
      const deletions = parseInt(parts[1]) || 0;

      return {
        additions,
        deletions,
        net: additions - deletions
      };
    }
  } catch {
    // File might be untracked
  }

  return { additions: 0, deletions: 0, net: 0 };
}

/**
 * Categorize all changes
 */
function categorizeChanges(fileDetails) {
  const categories = {
    code: { files: [], count: 0, additions: 0, deletions: 0 },
    documentation: { files: [], count: 0, additions: 0, deletions: 0 },
    configuration: { files: [], count: 0, additions: 0, deletions: 0 },
    test: { files: [], count: 0, additions: 0, deletions: 0 },
    style: { files: [], count: 0, additions: 0, deletions: 0 },
    other: { files: [], count: 0, additions: 0, deletions: 0 }
  };

  fileDetails.forEach(detail => {
    const category = detail.fileType;
    if (categories[category]) {
      categories[category].files.push(detail.file);
      categories[category].count++;
      categories[category].additions += detail.stats.additions;
      categories[category].deletions += detail.stats.deletions;
    } else {
      categories.other.files.push(detail.file);
      categories.other.count++;
      categories.other.additions += detail.stats.additions;
      categories.other.deletions += detail.stats.deletions;
    }
  });

  // Remove empty categories
  Object.keys(categories).forEach(key => {
    if (categories[key].count === 0) {
      delete categories[key];
    } else {
      // Limit files list to 20 per category
      categories[key].files = categories[key].files.slice(0, 20);
    }
  });

  return categories;
}

/**
 * Generate human-readable summary
 */
function generateSummary(fileDetails, categories) {
  if (fileDetails.length === 0) {
    return 'No changes detected in git repository';
  }

  const parts = [];

  // Count by change type
  const added = fileDetails.filter(f => f.changeType === 'added').length;
  const modified = fileDetails.filter(f => f.changeType === 'modified').length;
  const deleted = fileDetails.filter(f => f.changeType === 'deleted').length;

  if (added > 0) parts.push(`${added} added`);
  if (modified > 0) parts.push(`${modified} modified`);
  if (deleted > 0) parts.push(`${deleted} deleted`);

  let summary = `Modified ${fileDetails.length} file${fileDetails.length !== 1 ? 's' : ''}`;
  if (parts.length > 0) {
    summary += ` (${parts.join(', ')})`;
  }

  // Add category breakdown
  const categoryParts = [];
  const categoryOrder = ['code', 'documentation', 'configuration', 'test'];

  categoryOrder.forEach(cat => {
    if (categories[cat] && categories[cat].count > 0) {
      categoryParts.push(`${categories[cat].count} ${cat}`);
    }
  });

  if (categoryParts.length > 0) {
    summary += `: ${categoryParts.join(', ')}`;
  }

  return summary;
}

/**
 * Create empty analysis for error cases
 */
function createEmptyAnalysis(reason) {
  return {
    timestamp: new Date().toISOString(),
    projectPath: process.cwd(),
    sinceCommit: null,
    summary: reason,
    categories: {},
    fileDetails: [],
    diffStat: { filesChanged: 0, additions: 0, deletions: 0 },
    metadata: {
      totalFiles: 0,
      totalAdditions: 0,
      totalDeletions: 0,
      netChange: 0
    }
  };
}

/**
 * Get commit history for context
 */
function getRecentCommits(count = 5) {
  try {
    const output = execSync(`git log -${count} --pretty=format:"%h|%an|%ar|%s"`, {
      encoding: 'utf8',
      stdio: 'pipe'
    });

    return output.trim().split('\n').map(line => {
      const [hash, author, date, message] = line.split('|');
      return { hash, author, date, message };
    });
  } catch {
    return [];
  }
}

/**
 * Get current branch name
 */
function getCurrentBranch() {
  try {
    return execSync('git rev-parse --abbrev-ref HEAD', {
      encoding: 'utf8',
      stdio: 'pipe'
    }).trim();
  } catch {
    return 'unknown';
  }
}

module.exports = {
  analyzeGitChanges,
  getRecentCommits,
  getCurrentBranch,
  categorizeFileType,
  isGitRepository
};


