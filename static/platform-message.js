(function () {
    const existing = document.querySelector('[data-xg-message-widget]');
    if (existing) return;

    const state = {
        open: false,
    };

    const quickQuestions = [
        '上传文件失败怎么办？',
        '模板怎么保存到我的模板？',
        '处理结果在哪里下载？',
        '怎么开通团队版？'
    ];

    const quickTiles = ['预约演示', '试用申请', '功能建议', '帮助文档'];
    const chips = ['上传问题', '模板问题', '价格方案', '账号安全'];

    const root = document.createElement('div');
    root.dataset.xgMessageWidget = 'true';
    root.innerHTML = `
        <button class="xg-message-launcher" type="button" aria-expanded="false" aria-controls="xg-message-panel">
            <span class="xg-message-launcher-icon" aria-hidden="true">···</span>
            <span class="xg-message-launcher-label">消息</span>
            <span class="xg-message-launcher-dot" aria-hidden="true"></span>
        </button>
        <section class="xg-message-shell" id="xg-message-panel" aria-label="序光消息助手">
            <header class="xg-message-header">
                <div class="xg-message-brand">
                    <span class="xg-message-brand-mark" aria-hidden="true">序</span>
                    <span>序光消息助手</span>
                </div>
                <div class="xg-message-actions">
                    <button class="xg-message-text-btn" type="button" data-xg-message-minimize>收起</button>
                    <button class="xg-message-close" type="button" aria-label="关闭消息面板" data-xg-message-close>×</button>
                </div>
            </header>
            <div class="xg-message-body">
                <div class="xg-message-time">刚刚</div>
                <div class="xg-message-note">温馨提示：这里是演示消息入口，后续可接入工单、在线消息和团队通知。请勿在演示环境提交敏感信息。</div>
                <article class="xg-message-card">
                    <h3>Hi，你好</h3>
                    <p>我是序光助手，可以解答上传、模板、账号、价格、数据处理和工作台相关问题。</p>
                    ${quickQuestions.map(item => `
                        <button class="xg-message-question" type="button" data-xg-message-fill="${escapeHtml(item)}">
                            <span>${escapeHtml(item)}</span>
                            <em>提问</em>
                        </button>
                    `).join('')}
                </article>
                <div class="xg-message-grid">
                    ${quickTiles.map(item => `<button class="xg-message-tile" type="button" data-xg-message-fill="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join('')}
                </div>
                <div class="xg-message-chips">
                    ${chips.map(item => `<button class="xg-message-chip" type="button" data-xg-message-fill="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join('')}
                </div>
                <div class="xg-message-chat" data-xg-message-chat></div>
            </div>
            <form class="xg-message-input" data-xg-message-form>
                <input type="text" name="message" autocomplete="off" placeholder="输入你想咨询的问题..." />
                <button type="submit">发送</button>
            </form>
        </section>
    `;

    const mount = () => {
        document.body.appendChild(root);
        bindWidget();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', mount, { once: true });
    } else {
        mount();
    }

    function bindWidget() {
        const launcher = root.querySelector('.xg-message-launcher');
        const panel = root.querySelector('.xg-message-shell');
        const form = root.querySelector('[data-xg-message-form]');
        const input = form.querySelector('input');
        const chat = root.querySelector('[data-xg-message-chat]');

        const setOpen = (nextOpen) => {
            state.open = nextOpen;
            panel.classList.toggle('is-open', nextOpen);
            launcher.setAttribute('aria-expanded', String(nextOpen));
            if (nextOpen) {
                root.querySelector('.xg-message-launcher-dot').style.display = 'none';
                setTimeout(() => input.focus(), 60);
            }
        };

        launcher.addEventListener('click', () => setOpen(!state.open));
        root.querySelector('[data-xg-message-close]').addEventListener('click', () => setOpen(false));
        root.querySelector('[data-xg-message-minimize]').addEventListener('click', () => setOpen(false));

        root.querySelectorAll('[data-xg-message-fill]').forEach(button => {
            button.addEventListener('click', () => {
                input.value = button.dataset.xgMessageFill || '';
                setOpen(true);
                input.focus();
            });
        });

        form.addEventListener('submit', event => {
            event.preventDefault();
            const value = input.value.trim();
            if (!value) return;
            addBubble(chat, value, true);
            input.value = '';
            setTimeout(() => {
                addBubble(chat, buildReply(value), false);
                chat.scrollIntoView({ block: 'end', behavior: 'smooth' });
            }, 280);
        });

        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && state.open) setOpen(false);
        });
    }

    function addBubble(chat, message, isUser) {
        const bubble = document.createElement('div');
        bubble.className = `xg-message-bubble${isUser ? ' is-user' : ''}`;
        bubble.textContent = message;
        chat.appendChild(bubble);
        bubble.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    function buildReply(message) {
        if (message.includes('上传')) {
            return '可以先确认文件格式、文件大小和是否被其他软件占用。上传后文件会留在当前页面，点击“开始处理”后才会生成结果。';
        }
        if (message.includes('模板')) {
            return '自定义模板会进入“我的模板”。后续可以补充预览图、标签和搜索关键词，方便团队复用。';
        }
        if (message.includes('价格') || message.includes('团队')) {
            return '价格页包含免费版、专业版、团队版和企业版。团队版适合多人协作、共享空间和权限管理。';
        }
        if (message.includes('账号') || message.includes('安全')) {
            return '账号与安全可以管理资料、绑定账号、通知偏好、数据记录和注销账号。';
        }
        return '我已经收到你的问题。当前是前端演示回复，正式接入后会把问题同步到消息与工单系统。';
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }
})();
