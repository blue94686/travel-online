export default function LayoutModuleCard({ className = '', children, ...props }) {
  return <section className={`preview-module ${className}`} {...props}>{children}</section>
}
