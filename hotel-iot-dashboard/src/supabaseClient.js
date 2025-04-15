import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://blmpxixwblzyzxvygalm.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJsbXB4aXh3Ymx6eXp4dnlnYWxtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyMTA3NzUsImV4cCI6MjA1OTc4Njc3NX0.4NnTOmuhMGTFjsCXIPrwK4peYg1KPtDxGeRTU_qsEbU';

export const supabase = createClient(supabaseUrl, supabaseKey);
