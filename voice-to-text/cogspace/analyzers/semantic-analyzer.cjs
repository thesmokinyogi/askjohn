// COGSPACE v40.0.0
/**
 * COGSPACE v32.0.0 Semantic Analyzer
 * Extracts "what", "why", and "how" from session data for AI understanding
 *
 * @module semantic-analyzer
 * @version 32.0.0
 */

const fs = require('fs');
const path = require('path');

/**
 * Analyzes session data to extract semantic meaning
 * @param {Object} sessionData - Complete session context data
 * @returns {Object} Semantic analysis conforming to context-schema.json
 */
function analyzeSemanticContext(sessionData) {
  const {
    toolUsage = [],
    conversationSummary = '',
    achievements = [],
    challenges = [],
    workDescription = '',
    currentFocus = '',
    nextActions = []
  } = sessionData;

  // Extract what was done
  const what = extractWhat(toolUsage, achievements, workDescription);

  // Extract why it matters
  const why = extractWhy(currentFocus, nextActions, conversationSummary);

  // Extract how it was approached
  const how = extractHow(toolUsage, workDescription);

  // Classify the work
  const workClassification = classifyWork(toolUsage, achievements, workDescription);

  // Determine outcomes
  const outcomes = determineOutcomes(achievements, challenges, toolUsage);

  // Build complete semantic context
  return {
    timestamp: new Date().toISOString(),
    sessionId: sessionData.sessionId || generateSessionId(),
    semanticSummary: {
      what: what.substring(0, 500), // Schema max length
      why: why.substring(0, 500),
      how: how.substring(0, 500)
    },
    workClassification,
    outcomes,
    toolsUsed: formatToolUsage(toolUsage),
    relatedGoals: extractRelatedGoals(sessionData),
    metadata: {
      projectName: sessionData.projectName || 'unknown',
      sessionDuration: sessionData.sessionDuration || '00:00:00',
      cogspaceVersion: '32.0.0',
      aiModel: sessionData.aiModel || 'claude-sonnet-4-5'
    }
  };
}

/**
 * Extract the "what" - concrete actions and deliverables
 */
function extractWhat(toolUsage, achievements, workDescription) {
  const actions = [];

  // Parse achievements
  if (achievements && achievements.length > 0) {
    actions.push(...achievements.slice(0, 3)); // Top 3 achievements
  }

  // Parse tool usage for actions
  const fileActions = [];
  toolUsage.forEach(tool => {
    if (tool.name === 'Write') fileActions.push(`created ${tool.count} files`);
    if (tool.name === 'Edit') fileActions.push(`modified ${tool.count} files`);
    if (tool.name === 'Read') fileActions.push(`analyzed ${tool.count} files`);
  });

  if (fileActions.length > 0) {
    actions.push(fileActions.join(', '));
  }

  // Fallback to work description
  if (actions.length === 0 && workDescription) {
    const firstSentence = workDescription.split('.')[0];
    actions.push(firstSentence);
  }

  const what = actions.join('; ') || 'Session work completed';
  return what.length >= 10 ? what : 'Completed session activities and made progress on project objectives';
}

/**
 * Extract the "why" - purpose, motivation, impact
 */
function extractWhy(currentFocus, nextActions, conversationSummary) {
  const reasons = [];

  // Parse current focus for purpose
  if (currentFocus && currentFocus.length > 10) {
    reasons.push(`To ${currentFocus.toLowerCase()}`);
  }

  // Parse next actions for forward-looking purpose
  if (nextActions && nextActions.length > 0) {
    const nextAction = nextActions[0];
    if (typeof nextAction === 'string' && nextAction.length > 10) {
      reasons.push(`enabling ${nextAction.toLowerCase()}`);
    }
  }

  // Extract impact from conversation
  if (conversationSummary) {
    const impactKeywords = ['improve', 'enhance', 'enable', 'support', 'facilitate'];
    for (const keyword of impactKeywords) {
      if (conversationSummary.toLowerCase().includes(keyword)) {
        const sentence = conversationSummary.split('.').find(s =>
          s.toLowerCase().includes(keyword)
        );
        if (sentence && sentence.length > 10) {
          reasons.push(sentence.trim());
          break;
        }
      }
    }
  }

  const why = reasons.join(' and ') || 'To advance project objectives and improve system capabilities';
  return why.length >= 10 ? why : 'To advance project objectives and improve system capabilities';
}

/**
 * Extract the "how" - methodology, tools, techniques
 */
function extractHow(toolUsage, workDescription) {
  const methods = [];

  // Describe tool usage methodology
  if (toolUsage && toolUsage.length > 0) {
    const primaryTools = toolUsage
      .filter(t => t.count > 0)
      .sort((a, b) => b.count - a.count)
      .slice(0, 3)
      .map(t => t.name);

    if (primaryTools.length > 0) {
      methods.push(`Using ${primaryTools.join(', ')} tools`);
    }
  }

  // Parse work description for methodology
  const methodKeywords = ['implemented', 'created', 'analyzed', 'designed', 'tested', 'validated'];
  for (const keyword of methodKeywords) {
    if (workDescription && workDescription.toLowerCase().includes(keyword)) {
      methods.push(`through ${keyword} approach`);
      break;
    }
  }

  // Add collaborative approach if applicable
  if (workDescription && workDescription.toLowerCase().includes('review')) {
    methods.push('with iterative review and refinement');
  }

  const how = methods.join(' ') || 'Through systematic development and validation processes';
  return how.length >= 10 ? how : 'Through systematic development and validation processes';
}

/**
 * Classify the work type and domains
 */
function classifyWork(toolUsage, achievements, workDescription) {
  const text = (workDescription + ' ' + achievements.join(' ')).toLowerCase();

  // Determine primary work type
  let primaryType = 'implementation';
  const typePatterns = {
    implementation: /implement|create|build|develop|code/,
    analysis: /analyze|review|investigate|examine/,
    debugging: /debug|fix|resolve|troubleshoot/,
    refactoring: /refactor|improve|optimize|clean/,
    documentation: /document|write|explain|guide/,
    testing: /test|validate|verify|check/,
    planning: /plan|design|architect|strategy/
  };

  for (const [type, pattern] of Object.entries(typePatterns)) {
    if (pattern.test(text)) {
      primaryType = type;
      break;
    }
  }

  // Determine domains
  const domains = new Set();
  const domainPatterns = {
    frontend: /ui|component|react|vue|css|html/,
    backend: /api|server|database|endpoint/,
    infrastructure: /deploy|docker|ci|cd|container/,
    security: /security|auth|encrypt|vulnerability/,
    performance: /performance|optimize|speed|efficient/,
    documentation: /document|readme|guide|wiki/,
    testing: /test|spec|coverage|validation/,
    architecture: /architecture|design|pattern|structure/
  };

  for (const [domain, pattern] of Object.entries(domainPatterns)) {
    if (pattern.test(text)) {
      domains.add(domain);
    }
  }

  // If no domains found, infer from tools
  if (domains.size === 0) {
    const hasWrites = toolUsage.some(t => t.name === 'Write' && t.count > 0);
    const hasReads = toolUsage.some(t => t.name === 'Read' && t.count > 0);

    if (hasWrites) domains.add('implementation');
    if (hasReads) domains.add('analysis');
  }

  // Ensure at least one domain
  if (domains.size === 0) {
    domains.add('other');
  }

  // Determine complexity
  const complexity = determineComplexity(toolUsage, achievements, text);

  return {
    primaryType,
    domains: Array.from(domains).slice(0, 5), // Max 5 domains
    complexity,
    focusArea: extractFocusArea(text)
  };
}

/**
 * Determine work complexity
 */
function determineComplexity(toolUsage, achievements, text) {
  let score = 0;

  // Tool diversity indicates complexity
  const uniqueTools = new Set(toolUsage.map(t => t.name)).size;
  if (uniqueTools > 5) score += 2;
  else if (uniqueTools > 3) score += 1;

  // Number of achievements
  if (achievements.length > 5) score += 2;
  else if (achievements.length > 2) score += 1;

  // Text indicators
  if (text.includes('complex') || text.includes('comprehensive')) score += 1;
  if (text.includes('critical') || text.includes('advanced')) score += 1;

  // Map score to complexity level
  if (score >= 4) return 'complex';
  if (score >= 2) return 'moderate';
  return 'simple';
}

/**
 * Extract focus area from text
 */
function extractFocusArea(text) {
  // Try to find specific focus mentions
  const focusPatterns = [
    /focus(?:ed|ing)? on ([^,.]+)/i,
    /working on ([^,.]+)/i,
    /implementing ([^,.]+)/i,
    /building ([^,.]+)/i
  ];

  for (const pattern of focusPatterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      return match[1].trim().substring(0, 200);
    }
  }

  return 'Project objectives and deliverables';
}

/**
 * Determine outcomes from session
 */
function determineOutcomes(achievements, challenges, toolUsage) {
  const achieved = achievements.map(a =>
    typeof a === 'string' ? a.substring(0, 200) : String(a).substring(0, 200)
  );

  const blockers = challenges.map(c => {
    const challengeText = typeof c === 'string' ? c : String(c);
    return {
      description: challengeText.substring(0, 200),
      severity: challengeText.toLowerCase().includes('critical') ? 'critical' :
                challengeText.toLowerCase().includes('block') ? 'high' : 'medium',
      resolved: false
    };
  });

  // Determine impact
  const impactLevel = achieved.length > 5 ? 'significant' :
                     achieved.length > 2 ? 'moderate' : 'minimal';

  const impact = {
    level: impactLevel,
    description: `Completed ${achieved.length} deliverables with ${blockers.length} issues encountered`,
    metrics: {
      achievementCount: achieved.length,
      blockerCount: blockers.length,
      toolsUsed: toolUsage.length
    }
  };

  return {
    achieved: achieved.slice(0, 10), // Max 10 achievements
    blockers: blockers.slice(0, 5),   // Max 5 blockers
    impact,
    learnings: extractLearnings(achievements, challenges)
  };
}

/**
 * Extract learnings from session
 */
function extractLearnings(achievements, challenges) {
  const learnings = [];

  // Learning from achievements
  if (achievements.length > 3) {
    learnings.push('Systematic approach to complex tasks yields consistent results');
  }

  // Learning from challenges
  if (challenges.length > 0) {
    learnings.push('Early identification of blockers enables faster resolution');
  }

  return learnings;
}

/**
 * Format tool usage for schema
 */
function formatToolUsage(toolUsage) {
  return toolUsage
    .filter(t => t.count > 0)
    .map(t => ({
      name: t.name,
      count: t.count,
      purpose: t.purpose || inferToolPurpose(t.name)
    }));
}

/**
 * Infer tool purpose from name
 */
function inferToolPurpose(toolName) {
  const purposes = {
    'Write': 'Create new files and content',
    'Edit': 'Modify existing files',
    'Read': 'Analyze and understand code',
    'Bash': 'Execute commands and operations',
    'Grep': 'Search and find patterns',
    'Glob': 'Find files by pattern',
    'TodoWrite': 'Track tasks and progress'
  };
  return purposes[toolName] || `Perform ${toolName} operations`;
}

/**
 * Extract related goals from session data
 */
function extractRelatedGoals(sessionData) {
  const goals = [];

  if (sessionData.relatedGoals) {
    goals.push(...sessionData.relatedGoals);
  }

  // Extract from text if available
  const text = JSON.stringify(sessionData);
  const goalPattern = /goal-\d+-[a-f0-9]+/g;
  const matches = text.match(goalPattern);

  if (matches) {
    goals.push(...matches);
  }

  return [...new Set(goals)]; // Deduplicate
}

/**
 * Generate session ID if not provided
 */
function generateSessionId() {
  const timestamp = Date.now();
  const hash = Math.random().toString(36).substring(2, 10);
  return `${timestamp}-${hash}`;
}

/**
 * Validate semantic context against schema
 */
function validateSemanticContext(context, schemaPath) {
  try {
    const Ajv = require('ajv');
    const addFormats = require('ajv-formats');
    const ajv = new Ajv({ strictTypes: false });
    addFormats(ajv);

    const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));
    const validate = ajv.compile(schema);
    const valid = validate(context);

    if (!valid) {
      console.error('Validation errors:', validate.errors);
      return false;
    }

    return true;
  } catch (error) {
    console.error('Validation error:', error.message);
    return false;
  }
}

module.exports = {
  analyzeSemanticContext,
  validateSemanticContext,
  extractWhat,
  extractWhy,
  extractHow,
  classifyWork,
  determineOutcomes
};


