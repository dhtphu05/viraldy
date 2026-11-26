import type { AuthIntent } from "./auth-flow";

type AuthMode = "local_test" | "oidc" | "password" | "unavailable";

export type AuthPagePresentation = {
    eyebrow: string;
    title: string;
    description: string;
    ctaLabel: string;
    showDevAccount: boolean;
};

export function authPagePresentation(mode: AuthMode, intent: AuthIntent): AuthPagePresentation {
    if (mode === "password") {
        return intent === "signup"
            ? {
                  eyebrow: "Bắt đầu",
                  title: "Tạo tài khoản Viraldy",
                  description: "Tạo tài khoản để bắt đầu làm việc cùng đội ngũ của bạn.",
                  ctaLabel: "Tạo tài khoản",
                  showDevAccount: false,
              }
            : {
                  eyebrow: "Chào mừng bạn trở lại",
                  title: "Đăng nhập vào Viraldy",
                  description: "Sử dụng email và mật khẩu để truy cập không gian làm việc của bạn.",
                  ctaLabel: "Đăng nhập",
                  showDevAccount: false,
              };
    }

    if (mode === "unavailable") {
        return intent === "signup"
            ? {
                  eyebrow: "Tạm thời không thể truy cập",
                  title: "Tạm thời không thể tạo tài khoản",
                  description: "Dịch vụ xác thực chưa sẵn sàng. Vui lòng thử lại sau ít phút.",
                  ctaLabel: "Không thể tạo tài khoản",
                  showDevAccount: false,
              }
            : {
                  eyebrow: "Tạm thời không thể truy cập",
                  title: "Tạm thời không thể đăng nhập",
                  description: "Dịch vụ xác thực chưa sẵn sàng. Vui lòng thử lại sau ít phút.",
                  ctaLabel: "Không thể đăng nhập",
                  showDevAccount: false,
              };
    }

    if (mode === "local_test") {
        return intent === "signup"
            ? {
                  eyebrow: "Thiết lập thử nghiệm",
                  title: "Tạo tài khoản thử nghiệm",
                  description:
                      "Bắt đầu với hồ sơ thử nghiệm có sẵn email, họ tên và số điện thoại.",
                  ctaLabel: "Tạo tài khoản thử nghiệm và tiếp tục",
                  showDevAccount: true,
              }
            : {
                  eyebrow: "Truy cập thử nghiệm",
                  title: "Đăng nhập vào Viraldy",
                  description:
                      "Sử dụng tài khoản thử nghiệm bên dưới để truy cập không gian làm việc chỉ với một lần nhấn.",
                  ctaLabel: "Đăng nhập bằng tài khoản thử nghiệm",
                  showDevAccount: true,
              };
    }

    return intent === "signup"
        ? {
              eyebrow: "Bắt đầu",
              title: "Tạo tài khoản Viraldy",
              description:
                  "Tạo tài khoản qua nhà cung cấp danh tính để truy cập không gian làm việc của bạn.",
              ctaLabel: "Tạo tài khoản an toàn",
              showDevAccount: false,
          }
        : {
              eyebrow: "Chào mừng bạn trở lại",
              title: "Chào mừng bạn trở lại",
              description:
                  "Tiếp tục bằng danh tính đã xác minh. Bạn sẽ được chuyển về trang đã yêu cầu.",
              ctaLabel: "Tiếp tục đăng nhập an toàn",
              showDevAccount: false,
          };
}

export function passwordAuthErrorMessage(status: number): string {
    switch (status) {
        case 0:
            return "Không thể kết nối. Vui lòng kiểm tra kết nối mạng và thử lại.";
        case 400:
        case 422:
            return "Vui lòng kiểm tra thông tin và thử lại.";
        case 401:
            return "Email hoặc mật khẩu không chính xác. Vui lòng thử lại.";
        case 403:
            return "Tài khoản này hiện không thể đăng nhập. Vui lòng liên hệ quản trị viên không gian làm việc.";
        case 409:
            return "Tài khoản sử dụng email này đã tồn tại. Vui lòng đăng nhập.";
        case 429:
            return "Bạn đã thử quá nhiều lần. Vui lòng chờ ít phút rồi thử lại.";
        default:
            return "Hiện không thể hoàn tất đăng nhập. Vui lòng thử lại sau ít phút.";
    }
}
