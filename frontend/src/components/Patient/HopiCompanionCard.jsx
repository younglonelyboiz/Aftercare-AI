import React from 'react';
import { Bot, ArrowRight, Sparkles } from 'lucide-react';

export default function HopiCompanionCard({ onOpenChat }) {
  return (
    <section aria-label="Trợ lý ảo Hopi" className="bg-[#eff6ff] border border-[#dbeafe] rounded-[14px] p-5 space-y-4">
      {/* Mascot & Title */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-[10px] bg-white border border-[#dbeafe] flex items-center justify-center p-1 shrink-0">
          <img
            src="/pictures/hopi-mascot-clean.png"
            alt="Mascot Hopi"
            width={40}
            height={40}
            className="object-contain"
          />
        </div>
        <div>
          <h3 className="font-semibold text-[#172b3a] text-base flex items-center gap-1.5">
            Hopi đồng hành cùng bạn
            <Sparkles className="w-4 h-4 text-[#2568d4]" />
          </h3>
          <p className="text-xs text-[#475569] font-medium">
            Trợ lý AI hướng dẫn hen phế quản
          </p>
        </div>
      </div>

      {/* Description */}
      <p className="text-xs sm:text-sm text-[#475569] leading-relaxed font-normal">
        Bạn có thể trao đổi bất kỳ lúc nào về kỹ thuật hít bình xịt, nhận biết dấu hiệu bùng phát cơn hen và các lưu ý sinh hoạt sau xuất viện.
      </p>

      {/* Call to Action */}
      <button
        type="button"
        onClick={onOpenChat}
        className="w-full min-h-[42px] bg-[#2568d4] hover:bg-[#1d56b8] text-white rounded-lg font-semibold text-xs sm:text-sm px-4 py-2.5 flex items-center justify-between transition-colors cursor-pointer"
      >
        <span className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-blue-100" />
          Hỏi Trợ lý Hopi ngay
        </span>
        <ArrowRight className="w-4 h-4" />
      </button>
    </section>
  );
}
