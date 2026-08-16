import PortalAuthCard from '../../components/PortalAuthCard'

export default function UserPortalLogin() {
  return <PortalAuthCard mode="login" accountType="user" eyebrow="USER PORTAL / SIGN IN" title="Sign in to the User Portal" successHref="/portal" />
}
