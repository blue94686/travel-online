export default function ResponsivePreviewSwitch({ value, onChange }) {
  return (
    <select value={value} onChange={event => onChange?.(event.target.value)}>
      <option value="desktop">PC</option>
      <option value="tablet">平板</option>
      <option value="mobile">手机</option>
    </select>
  )
}
