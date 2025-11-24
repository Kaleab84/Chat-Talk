export const getGreeting = () => {
  if (typeof window === 'undefined') return '';
  try {
    const raw = (window.localStorage.getItem('displayName') || '').trim();
    if (!raw) return '';
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  } catch (error) {
    console.warn('Unable to read greeting from localStorage', error);
    return '';
  }
};
