import { Component, type ReactNode } from "react";

export default class SectionErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <section className="stack-md" role="alert">
        <div className="hero-card compact">
          <div>
            <span className="eyebrow">Page display error</span>
            <h1>This page could not be displayed</h1>
            <p>
              Your saved records have not been changed by this display error. If you were editing,
              check your last saved version before trying again. You can still use the navigation
              menu to open another page.
            </p>
          </div>
        </div>
        <div className="action-group">
          <button
            className="btn primary"
            type="button"
            onClick={() => this.setState({ failed: false })}
          >
            Try this page again
          </button>
          <button className="btn secondary" type="button" onClick={() => window.location.reload()}>
            Reload Cathedra
          </button>
        </div>
      </section>
    );
  }
}
