import PortalAuthCard from '../../components/PortalAuthCard'

export default function CreatorLogin() {
  return <PortalAuthCard mode="login" accountType="creator" eyebrow="AGENT CREATOR PORTAL" title="Sign in to your creator workspace" successHref="/creator" />
}
