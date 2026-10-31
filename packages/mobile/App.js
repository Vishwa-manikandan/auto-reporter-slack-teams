import React, { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView } from 'react-native';

export default function App() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const generateReport = async () => {
    setLoading(true);
    // Simulate API call to backend
    setTimeout(() => {
      setReport(`## Daily Status Report

### Blocked Issues:
1. [Medium] Deploy blocked due to config issue -> @user1

### Bugs:
1. [High Priority] Critical bug in auth flow -> @user2

### Action Items:
- [ ] Review PR by EOD -> @user3

---
Generated from mobile app`);
      setLoading(false);
    }, 1000);
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>📊 Auto-Reporter</Text>
        <Text style={styles.subtitle}>Slack Status Reports</Text>
      </View>

      <TouchableOpacity 
        style={styles.button} 
        onPress={generateReport}
        disabled={loading}
      >
        <Text style={styles.buttonText}>
          {loading ? 'Generating...' : 'Generate Report'}
        </Text>
      </TouchableOpacity>

      <ScrollView style={styles.reportContainer}>
        {report ? (
          <Text style={styles.reportText}>{report}</Text>
        ) : (
          <Text style={styles.placeholder}>No report generated yet</Text>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#667eea',
    paddingTop: 50,
  },
  header: {
    alignItems: 'center',
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
  },
  subtitle: {
    fontSize: 16,
    color: 'white',
    opacity: 0.9,
  },
  button: {
    backgroundColor: 'white',
    margin: 20,
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonText: {
    color: '#667eea',
    fontSize: 16,
    fontWeight: '600',
  },
  reportContainer: {
    flex: 1,
    backgroundColor: 'white',
    margin: 20,
    marginTop: 0,
    borderRadius: 10,
    padding: 15,
  },
  reportText: {
    fontFamily: 'monospace',
    fontSize: 12,
    lineHeight: 18,
  },
  placeholder: {
    textAlign: 'center',
    color: '#999',
    marginTop: 50,
  },
});
