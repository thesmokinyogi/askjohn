// COGSPACE v40.0.0
/**
 * COGSPACE v32.0.0 User Context Analyzer
 * Tracks user preferences and interaction patterns
 * @module user-context-analyzer
 * @version 32.0.0
 */

const fs = require('fs');
const path = require('path');

class UserContextAnalyzer {
  constructor() {
    this.sessionMessages = [];
  }

  /**
   * Analyze user interactions from session
   */
  analyzeUserContext(sessionData) {
    const messages = this.extractUserMessages(sessionData);
    const preferences = this.inferPreferences(messages, sessionData);
    const patterns = this.detectPatterns(messages, sessionData);
    const adaptations = this.suggestAdaptations(preferences, patterns);

    return {
      timestamp: new Date().toISOString(),
      sessionId: sessionData.sessionId || this.generateSessionId(),
      userInteractions: {
        messages: messages.map(this.enrichMessage.bind(this)),
        messageCount: messages.length,
        avgMessageLength: this.calculateAvgLength(messages)
      },
      preferences,
      patterns,
      adaptations,
      metadata: {
        projectName: sessionData.projectName || 'unknown',
        totalSessions: sessionData.totalSessions || 1,
        cogspaceVersion: '32.0.0'
      }
    };
  }

  extractUserMessages(sessionData) {
    const messages = [];
    const rawMessages = sessionData.userMessages || sessionData.messages || [];

    rawMessages.forEach((msg, idx) => {
      const timestamp = Date.now();
      if (typeof msg === 'string') {
        messages.push({
          messageId: 'msg-' + timestamp + '-' + idx,
          content: msg,
          timestamp: new Date().toISOString()
        });
      } else if (msg.content) {
        messages.push({
          messageId: msg.id || 'msg-' + timestamp + '-' + idx,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString()
        });
      }
    });

    return messages;
  }

  enrichMessage(msg) {
    return {
      ...msg,
      intent: this.classifyIntent(msg.content),
      context: this.extractContext(msg.content),
      sentiment: this.detectSentiment(msg.content)
    };
  }

  classifyIntent(content) {
    // Ensure content is a string
    if (typeof content !== 'string') {
      content = String(content || '');
    }

    const lower = content.toLowerCase();
    let primary = 'request';

    if (lower.includes('?')) primary = 'question';
    if (lower.includes('thank') || lower.includes('great')) primary = 'feedback';
    if (lower.includes('yes') || lower.includes('no') || lower.includes('ok')) primary = 'approval';
    if (lower.includes('how') || lower.includes('why') || lower.includes('explain')) primary = 'clarification';

    return {
      primary,
      confidence: 0.8
    };
  }

  extractContext(content) {
    // Ensure content is a string
    if (typeof content !== 'string') {
      content = String(content || '');
    }

    const context = {
      topics: []
    };

    const topicKeywords = ['test', 'build', 'deploy', 'fix', 'implement', 'design', 'analyze'];
    topicKeywords.forEach(keyword => {
      if (content.toLowerCase().includes(keyword)) {
        context.topics.push(keyword);
      }
    });

    return context;
  }

  detectSentiment(content) {
    // Ensure content is a string
    if (typeof content !== 'string') {
      content = String(content || '');
    }

    const lower = content.toLowerCase();
    const positive = ['great', 'excellent', 'perfect', 'thank', 'good', 'awesome'];
    const negative = ['issue', 'problem', 'error', 'wrong', 'fail'];

    const posCount = positive.filter(w => lower.includes(w)).length;
    const negCount = negative.filter(w => lower.includes(w)).length;

    if (posCount > negCount) return 'positive';
    if (negCount > posCount) return 'negative';
    return 'neutral';
  }

  inferPreferences(messages, sessionData) {
    return {
      communicationStyle: {
        verbosity: this.inferVerbosity(messages),
        technicalDepth: 'advanced',
        explanationStyle: 'collaborative'
      },
      workingStyle: {
        pace: 'steady',
        approach: 'methodical'
      }
    };
  }

  inferVerbosity(messages) {
    const avgLength = this.calculateAvgLength(messages);
    if (avgLength > 200) return 'detailed';
    if (avgLength > 100) return 'balanced';
    return 'concise';
  }

  detectPatterns(messages, sessionData) {
    return {
      sessionPatterns: {
        frequencyPattern: 'regular'
      },
      communicationPatterns: {
        messageComplexity: messages.length > 5 ? 'complex' : 'moderate'
      }
    };
  }

  suggestAdaptations(preferences, patterns) {
    return {
      responseStyle: {
        currentVerbosity: preferences.communicationStyle.verbosity,
        adaptationReason: 'Based on user message patterns'
      }
    };
  }

  calculateAvgLength(messages) {
    if (messages.length === 0) return 0;
    const total = messages.reduce((sum, msg) => sum + msg.content.length, 0);
    return Math.round(total / messages.length);
  }

  generateSessionId() {
    const timestamp = Date.now();
    const hash = Math.random().toString(36).substring(2, 10);
    return timestamp + '-' + hash;
  }
}

module.exports = UserContextAnalyzer;


