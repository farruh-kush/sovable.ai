import PortalAuthCard from '../../components/PortalAuthCard'

export default function AdminPortalLogin() {
  return <PortalAuthCard mode="login" accountType="admin" eyebrow="ADMIN PORTAL / SIGN IN" title="Sign in to the Admin Portal" successHref="/admin" />
}
