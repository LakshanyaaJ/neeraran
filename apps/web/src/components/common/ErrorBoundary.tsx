import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an unhandled exception:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[300px] flex items-center justify-center p-6">
          <div className="glass-panel p-8 max-w-md w-full text-center space-y-4 border-coral/30">
            <div className="w-12 h-12 mx-auto rounded-full bg-coral/10 text-coral flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 stroke-[1.5]" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold text-ink-900">
                {this.props.fallbackTitle || 'Component encountered a state exception'}
              </h3>
              <p className="text-sm text-ink-600">
                The digital twin recovered safely. You can reload this view or continue navigating.
              </p>
            </div>
            {this.state.error && (
              <p className="text-xs font-mono bg-mist p-2 rounded-btn text-ink-600 overflow-x-auto text-left">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-700 text-white text-sm font-medium rounded-btn transition-colors"
            >
              <RefreshCw className="w-4 h-4 stroke-[1.5]" />
              Reload View
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
