// types.ts

export interface VocabularyScheme {
  uri: string;
  label: string;
  description?: string; 
}

export interface ConceptNode {
  uri: string;
  pref_label: string;
  alt_labels: string[];
  children?: ConceptNode[] | null; 
}


export interface ImportResponse {
  status: string;
  filename: string;
  nodes_added: number;
  edges_added: number;
}