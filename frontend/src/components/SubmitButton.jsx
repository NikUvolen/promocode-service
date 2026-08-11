import { LoaderCircle } from 'lucide-react'

export default function SubmitButton({ loading, disabled = false, children }) {
  return (
    <button className="button button--primary button--submit" disabled={loading || disabled} type="submit">
      {loading && <LoaderCircle className="spin" size={19} />}
      <span>{loading ? 'Подождите...' : children}</span>
    </button>
  )
}
