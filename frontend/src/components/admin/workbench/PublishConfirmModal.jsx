export default function PublishConfirmModal({ onPublish, onCancel }) {
  return <div className="modal-panel"><h2>发布确认</h2><p>发布后前台会读取最新已启用布局。</p><div className="admin-actions"><button className="primary-btn" onClick={onPublish}>确认发布</button><button onClick={onCancel}>取消</button></div></div>
}
