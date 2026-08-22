import PortalAuthCard from '../../components/PortalAuthCard'

export default function RegisterPage() {
  return <PortalAuthCard mode="register" accountType="user" eyebrow="ACCOUNT REGISTER" title="Start with your identity" successHref="/portal" />
}
