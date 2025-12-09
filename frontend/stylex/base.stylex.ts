import stylex from '@stylexjs/stylex';
import { tokens } from './variables.stylex';

export const baseStyles = stylex.create({
  // Layout styles
  container: {
    flex: 1,
    backgroundColor: tokens.colors.background,
  },
  center: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  row: {
    flexDirection: 'row',
  },
  spaceBetween: {
    justifyContent: 'space-between',
  },
  // Text styles
  text: {
    color: tokens.colors.text,
  },
  heading: {
    fontSize: tokens.fontSize['2xl'],
    fontWeight: 'bold',
    color: tokens.colors.text,
  },
  subheading: {
    fontSize: tokens.fontSize.xl,
    fontWeight: '600',
    color: tokens.colors.text,
  },
  body: {
    fontSize: tokens.fontSize.md,
    color: tokens.colors.text,
  },
  caption: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.icon, // Using icon color for secondary text
  },
  // Card styles
  card: {
    backgroundColor: tokens.colors.background,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.borderRadius.lg,
    padding: tokens.spacing.md,
    ...tokens.shadow.md,
  },
  // Button styles
  button: {
    backgroundColor: tokens.colors.tint,
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.md,
    borderRadius: tokens.borderRadius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: {
    color: '#fff', // White text on colored buttons
    fontWeight: '600',
  },
  // Input styles
  input: {
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.borderRadius.md,
    padding: tokens.spacing.md,
    color: tokens.colors.text,
    backgroundColor: tokens.colors.background,
  },
  // Spacing utilities
  p_xs: { padding: tokens.spacing.xs },
  p_sm: { padding: tokens.spacing.sm },
  p_md: { padding: tokens.spacing.md },
  p_lg: { padding: tokens.spacing.lg },
  p_xl: { padding: tokens.spacing.xl },

  m_xs: { margin: tokens.spacing.xs },
  m_sm: { margin: tokens.spacing.sm },
  m_md: { margin: tokens.spacing.md },
  m_lg: { margin: tokens.spacing.lg },
  m_xl: { margin: tokens.spacing.xl },

  pt_xs: { paddingTop: tokens.spacing.xs },
  pt_sm: { paddingTop: tokens.spacing.sm },
  pt_md: { paddingTop: tokens.spacing.md },
  pt_lg: { paddingTop: tokens.spacing.lg },
  pt_xl: { paddingTop: tokens.spacing.xl },

  pb_xs: { paddingBottom: tokens.spacing.xs },
  pb_sm: { paddingBottom: tokens.spacing.sm },
  pb_md: { paddingBottom: tokens.spacing.md },
  pb_lg: { paddingBottom: tokens.spacing.lg },
  pb_xl: { paddingBottom: tokens.spacing.xl },

  pl_xs: { paddingLeft: tokens.spacing.xs },
  pl_sm: { paddingLeft: tokens.spacing.sm },
  pl_md: { paddingLeft: tokens.spacing.md },
  pl_lg: { paddingLeft: tokens.spacing.lg },
  pl_xl: { paddingLeft: tokens.spacing.xl },

  pr_xs: { paddingRight: tokens.spacing.xs },
  pr_sm: { paddingRight: tokens.spacing.sm },
  pr_md: { paddingRight: tokens.spacing.md },
  pr_lg: { paddingRight: tokens.spacing.lg },
  pr_xl: { paddingRight: tokens.spacing.xl },
});