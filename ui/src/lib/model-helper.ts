export function getSelectedModel(): string {
  if (typeof window !== 'undefined') {
    const storedModel = localStorage.getItem('selectedModel');
    return storedModel || 'llama3.1:8b-instruct-q4_0';
  } else {
    // Default model
    return 'llama3.1:8b-instruct-q4_0';
  }
}