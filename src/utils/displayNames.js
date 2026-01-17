// Shared utility functions for the Iller6 app

export const formatName = (str) => {
  return String(str || '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Subject display name overrides
export const subjectDisplayNames = {
  'medical_exam': 'Läkarexamen',
  'korkortsteori': 'Körkortsteori'
};

// Topic display name overrides
export const topicDisplayOverrides = {
  allmanmedicin: 'Allmänmedicin',
  oron_nasa_hals: 'Öron-näsa-hals',
  trafik_och_vagmarken: 'Trafik och Vägmärken'
};

export const getSubjectDisplayName = (subjectKey) => {
  return subjectDisplayNames[subjectKey] || formatName(subjectKey);
};

export const getTopicDisplayName = (topicKey) => {
  const key = String(topicKey || '').replace(/\.ya?ml$/i, '');
  return topicDisplayOverrides[key] || formatName(key);
};
