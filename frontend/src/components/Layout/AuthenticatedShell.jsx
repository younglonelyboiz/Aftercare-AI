import '@fontsource-variable/plus-jakarta-sans';
import '@fontsource-variable/jetbrains-mono';
import '../../styles/p052.css';

export default function AuthenticatedShell({ currentPortal, children }) {
  return <div className={`aftercare-app portal-${currentPortal}`}>{children}</div>;
}
